# rag_service\src\services\query_rag.py
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Callable
import time
import sys
import os
import re
import json
import numpy as np
import asyncio
from pydantic import BaseModel

# Ensure the parent directory is added to `sys.path` for consistent imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)
try:
    from .search_qdrant import search_qdrant, reconstruct_source, advanced_qdrant_search

except:
    from services.search_qdrant import search_qdrant, reconstruct_source, advanced_qdrant_search

# Imports from shared_libs
from shared_libs.llm_providers import ProviderFactory
from shared_libs.utils.logger import Logger
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.prompt_config import PromptConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.embeddings.embedder_factory import EmbedderFactory 

# Load configuration
config_loader = AppConfigLoader()
config = config_loader.config
EMBEDDING_MODE=os.getenv('EMBEDDING_MODE','local')
embedding_config = EmbeddingConfig.from_config_loader(config_loader)
factory = EmbedderFactory(embedding_config)
embedding_function = factory.create_embedder(EMBEDDING_MODE)  

# Configure logging
logger = Logger.get_logger(module_name=__name__)

prompt_config=PromptConfigLoader()

# Load the RAG prompt from config
rag_prompt = prompt_config.get_prompt('prompts').get('rag_prompt', {}).get('system_prompt', '')

# Log an appropriate warning if the prompt is empty
if not rag_prompt:
    logger.warning("RAG system prompt is empty or not found in prompts configuration.")
else:
    logger.info("RAG system prompt loaded successfully.")

# Load the default LLM provider using ProviderFactory
default_provider_name = config.get('llm', {}).get('provider', 'groq')
default_llm_settings = config.get('llm', {}).get(default_provider_name, {})
llm_provider = ProviderFactory.get_provider(name=default_provider_name, config=default_llm_settings)

class QueryResponse(BaseModel):
    query_text: str
    response_text: str
    sources: List[str]
    timestamp: int

DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() in ["true", "1", "yes"]

def initialize_provider(llm_provider_name: Optional[str] = None) -> Any:
    """
    Initialize the LLM provider.
    """
    if llm_provider_name:
        logger.debug(f"Initializing LLM provider '{llm_provider_name}'")
        llm_settings = config.get('llm', {}).get(llm_provider_name, {})
        if not llm_settings:
            logger.error(f"LLM provider settings for '{llm_provider_name}' not found. Using default provider.")
            provider = llm_provider
        else:
            try:
                provider = ProviderFactory.get_provider(name=llm_provider_name, config=llm_settings)
            except Exception as e:
                logger.error(f"Failed to initialize LLM provider '{llm_provider_name}': {e}. Using default provider.")
                provider = llm_provider
    else:
        provider = llm_provider
    return provider

async def generate_embedding(query_text: str, embedding_function: Callable) -> Optional[np.ndarray]:
    """
    Generate the embedding vector for the query using the provided embedding function.

    Args:
        query_text (str): The text to generate embeddings for.
        embedding_function (Callable): The embedding function or object.

    Returns:
        Optional[np.ndarray]: The embedding vector or None if an error occurs.
    """
    try:
        if callable(getattr(embedding_function, 'embed', None)):
            embedding_vector = embedding_function.embed(query_text)
        elif callable(embedding_function):
            embedding_vector = await embedding_function(query_text)
        else:
            raise ValueError("Invalid embedding function provided.")

        if embedding_vector is None:
            raise ValueError("Embedding vector is None.")

        # Convert to NumPy array explicitly
        return np.array(embedding_vector)
    except Exception as e:
        logger.error(f"Failed to generate embedding for query '{query_text}': {e}")
        return None


async def retrieve_documents(embedding_vector: np.ndarray, top_k: int = 6) -> List[Dict]:
    """
    Retrieve similar documents using Qdrant.
    """
    
    try:
        retrieved_docs = await search_qdrant(embedding_vector, top_k=top_k)
        return retrieved_docs
    except Exception as e:
        logger.error(f"Failed to retrieve documents: {e}")
        return []

async def paraphrase_query(query_text: str, provider: Any) -> Optional[str]:
    """
    Paraphrase the query using the LLM provider.
    """
    try:
        paraphrase_prompt = f"Viết lại câu hỏi sau đây sử dụng ngôn ngữ, thuật ngữ pháp lý:\n\n{query_text}"
        paraphrased_query = await provider.send_single_message(prompt=paraphrase_prompt)
        return paraphrased_query.strip()
    except Exception as e:
        logger.error(f"Failed to paraphrase query '{query_text}': {e}")
        return None

def reconstruct_sources(retrieved_docs: List[Dict]) -> None:
    """
    Reconstruct sources for documents where source is None.
    """
    for doc in retrieved_docs:
        if not doc.get("source"):
            doc["source"] = reconstruct_source(doc.get("chunk_id", "Unknown Record"))

async def rerank_documents(retrieved_docs: List[Dict], query_text: str, provider: Any) -> List[Dict]:
    """
    Rerank the retrieved documents based on their relevance to the query.
    """
    scored_docs = []
    for doc in retrieved_docs:
        content = doc.get('content', '')
        score = await get_relevance_score(query_text, content, provider)
        scored_docs.append((doc, score))

    # Sort documents by score in descending order
    scored_docs.sort(key=lambda x: x[1], reverse=True)

    # Return the sorted documents
    return [doc for doc, score in scored_docs]

# Placeholder function
async def get_relevance_score(query_text: str, doc_content: str, provider: Any) -> float:
    """
    Get the relevance score of a document to the query using the LLM.
    """
    try:
        prompt = f"On a scale of 1 to 10, how relevant is the following document to the query?\n\nQuery: {query_text}\n\nDocument: {doc_content}\n\nRelevance Score (1-10):"
        response = await provider.send_single_message(prompt=prompt)
        # Extract the score from the response
        match = re.search(r'\b([1-9]|10)\b', response)
        if match:
            score = int(match.group(1))
            return score
        else:
            return 5  # Default score if not parsed
    except Exception as e:
        logger.error(f"Failed to get relevance score: {e}")

        return 5  # Default score
    
async def extract_keywords(
    query_text: str,
    provider: Any,
    top_k: int = 10
) -> List[str]:
    """
    Extract top_k keywords from the user query using the LLM.

    :param query_text: The user's input query.
    :param provider: The LLM provider instance to interact with.
    :param top_k: Number of top keywords to extract.
    :return: List of extracted keywords.
    """
    if not query_text:
        logger.error("No query text provided for keyword extraction.")
        return []

    if provider is None:
        logger.error("No LLM provider instance provided.")
        return []

    try:
        # Prompt the LLM to extract keywords in JSON format
        prompt = (
            f"Extract the top {top_k} keywords from the following question and return them in a JSON array format.\n\n"
            f"The keywords must:\n"
            f"- Be in the same language as the question.\n"
            f"- Prioritize legal terms, concepts, and terminology likely to appear in legal documents, cases, or articles.\n"
            f"- Avoid overly broad or vague terms unless directly relevant.\n\n"
            f"Example:\n"
            f'Question: "thủ tục đăng ký thay đổi người đại diện theo pháp luật của doanh nghiệp?"\n'
            f'Return: {{"keywords": ["đăng ký kinh doanh", "người đại diện", "luật doanh nghiệp", "giấy phép kinh doanh", "thông tin doanh nghiệp", "đăng ký doanh nghiệp"]}}\n\n'
            f"Now, extract keywords for the following question:\n"
            f"Question: \"{query_text}\"\n\n"
            f"Return the keywords in this format:\n"
            f'{{"keywords": ["keyword1", "keyword2", "keyword3", ...]}}'
        )

        logger.debug(f"Sending prompt to LLM for keyword extraction: {prompt}")

        # Send the prompt to the LLM and get the response
        response = await provider.send_single_message(prompt=prompt)

        # Use regex to extract JSON from the response
        json_match = re.search(r'(?<=\{).*?(?=\})', response, re.DOTALL)
        if json_match:
            json_str = "{" + json_match.group(0) + "}"
            logger.debug(f"LLM response (JSON extracted): {json_str}")
            try:
                keywords_data = json.loads(json_str)
                keywords = keywords_data.get("keywords", [])
                if isinstance(keywords, list) and len(keywords) > 0:
                    logger.debug(f"Extracted Keywords: {keywords}")
                    return keywords
                else:
                    logger.warning("The 'keywords' field is invalid or empty.")
                    return []
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse JSON from LLM response: {je}")
                return []
        else:
            # If no JSON object is found, log and return fallback
            logger.warning("No valid JSON found in the LLM response. Falling back to plain text parsing.")
            list_match = re.findall(r'\b\w+\b', response)
            if list_match:
                keywords = list_match[:top_k]
                logger.debug(f"Extracted Keywords from plain text: {keywords}")
                return keywords
            else:
                logger.warning("No keywords found in the fallback plain text parsing.")
                return []

    except Exception as e:
        logger.error(f"Error during keyword extraction: {e}")
        return []


async def generate_llm_response(query_text: str, retrieved_docs: List[Dict], provider: Any) -> str:
    """
    Generate the response using the LLM provider by sending a JSON payload.
    """
    # Combine retrieved documents to form context for LLM
    context = "\n\n---------------------------\n\n".join([
        f"Document ID: {doc.get('document_id', 'N/A')}\n"
        f"Cơ sở pháp lý: {doc.get('source', 'N/A')}\n"
        f"Mô tả: {doc.get('title', 'N/A')}\n"
        f"Nội dung: {doc.get('content', 'No content available.')}\n"
        f"Record ID: {doc.get('record_id', 'N/A')}\n"
        f"Chunk ID: {doc.get('chunk_id', 'N/A')}\n"
        for doc in retrieved_docs if doc.get('content')
    ])

    # Limit the context length
    MAX_CONTEXT_LENGTH = 8000  # Adjust as needed
    if len(context) > MAX_CONTEXT_LENGTH:
        logger.warning("Context is too long, truncating.")
        context = context[:MAX_CONTEXT_LENGTH]

    # Prepare the messages for the chat completion API
    messages = [
        {
            "role": "system",
            "content": rag_prompt  # Ensure rag_prompt is loaded correctly
        },
        {
            "role": "user",
            "content": f"User Question: {query_text}\n\nRelated information:\n\n{context}"
        }
    ]

    # Validate messages
    for message in messages:
        if 'role' not in message or 'content' not in message:
            logger.error(f"Invalid message format: {message}")
            raise ValueError("Each message must have 'role' and 'content'.")

    # Construct the message payload with the messages
    message_payload = {
        "messages": messages
    }
    # DEBUG
    # logger.debug(f"Message payload being sent: {json.dumps(message_payload, indent=2)}")

    # Generate response using the LLM provider
    try:
        response_text = await provider.send_single_message(message_payload=message_payload)
        return response_text
    except Exception as e:
        logger.error(f"Failed to generate a response using the provider for query: '{query_text}'. Error: {str(e)}")
        return "An error occurred while generating the answer."



def create_final_response(query_text: str, response_text: str, retrieved_docs: List[Dict]) -> QueryResponse:
    """
    Create the final QueryResponse object.
    """
    # Add citations to the response
    if retrieved_docs:
        citation_texts = [f"[Record ID: {doc['record_id']}]" for doc in retrieved_docs if doc.get('content')]
        if citation_texts:
            response_text += "\n\nReferences: " + ", ".join(citation_texts)

    # Extract sources
    sources = [doc['record_id'] for doc in retrieved_docs]

    # Create the response
    query_response = QueryResponse(
        query_text=query_text,
        response_text=response_text,
        sources=sources,
        timestamp=int(time.time())
    )
    return query_response

async def query_rag(
    query_item,
    conversation_history: Optional[List] = None,
    provider: Optional[Any] = None,
    embedding_mode: Optional[str] = None,
    llm_provider_name: Optional[str] = None,
    rerank: bool = False,
    keyword_gen: bool=False,
) -> Dict[str, Any]:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query by searching both QA and DOC collections.
    
    Args:
        query_item: The query input model.
        conversation_history: Optional conversation history for context.
        provider: LLM provider.
        embedding_mode: Mode for embedding ('local' or 'api').
        llm_provider_name: Name of the LLM provider.
        rerank: Whether to apply reranking to the retrieved documents (default False).
        keyword_gen: Whether to apply keyword generator help retrieve documents (default False).
    
    Returns:
        Dict[str, Any]: RAG response with query_response and retrieved_docs.
    """
    query_text = query_item.query_text

    # Initialize provider if not provided
    provider = provider or initialize_provider(llm_provider_name)

    # Determine the embedding mode
    current_embedding_mode = embedding_mode.lower() if embedding_mode else config.get('embedding', {}).get('mode', 'local').lower()

    # Get the embedding function based on the mode
    embedding_config = EmbeddingConfig.from_config_loader(config_loader)
    factory = EmbedderFactory(embedding_config)

    if current_embedding_mode == "api":
        embedding_function = factory.create_embedder('ec2')
    elif current_embedding_mode == "local":
        embedding_function = factory.create_embedder('local')
    else:
        raise ValueError(f"Unsupported embedding mode: {current_embedding_mode}")

    # Generate embedding vector for the query
    embedding_vector = await generate_embedding(query_text, embedding_function)
    if embedding_vector is None:
        return {
            "query_response": QueryResponse(
                query_text=query_text,
                response_text="An error occurred while creating embedding.",
                sources=[],
                timestamp=int(time.time())
            ),
            "retrieved_docs": [] if DEVELOPMENT_MODE else None
        }

    # Retrieve documents with or without keyword generation
    QA_COLLECTION_NAME = os.getenv("QA_COLLECTION_NAME", "legal_qa")
    DOC_COLLECTION_NAME = os.getenv("DOC_COLLECTION_NAME", "legal_doc")
    all_retrieved_docs = []

    if keyword_gen:
        # Extract keywords and use advanced search
        for attempt in range(2):  # Retry extracting keywords up to 2 times
            try:
                logger.debug(f"Attempt {attempt + 1}: Extracting keywords for query: {query_text}")
                keywords = await extract_keywords(query_text, provider, top_k=10)

                # Ensure keywords is a list and not empty
                if isinstance(keywords, list) and len(keywords) > 0:
                    logger.debug(f"Keywords extracted: {keywords}")
                    qa_docs = await advanced_qdrant_search(
                        embedding_vector, keywords, collection_name=QA_COLLECTION_NAME, top_k=3
                    )
                    doc_chunks = await advanced_qdrant_search(
                        embedding_vector, keywords, collection_name=DOC_COLLECTION_NAME, top_k=6
                    )
                    all_retrieved_docs = qa_docs + doc_chunks
                    break  # Exit retry loop on success
                else:
                    logger.warning("Keyword extraction returned an invalid or empty list.")
            except Exception as e:
                logger.error(f"Error during keyword extraction: {e}")

        # Fallback to normal search if keyword generation fails
        if not all_retrieved_docs:
            logger.warning("Falling back to normal search_qdrant due to keyword generation failure.")
            qa_docs = await search_qdrant(embedding_vector, collection_name=QA_COLLECTION_NAME, top_k=3)
            doc_chunks = await search_qdrant(embedding_vector, collection_name=DOC_COLLECTION_NAME, top_k=6)
            all_retrieved_docs = qa_docs + doc_chunks

    else:
        # Normal search without keyword generation
        qa_docs = await search_qdrant(embedding_vector, collection_name=QA_COLLECTION_NAME, top_k=3)
        doc_chunks = await search_qdrant(embedding_vector, collection_name=DOC_COLLECTION_NAME, top_k=6)
        all_retrieved_docs = qa_docs + doc_chunks

    # Handle case with no retrieved documents
    if not all_retrieved_docs:
        logger.warning(f"No relevant documents found for query: '{query_text}'")
        response_text = "No relevant data found."
        query_response = QueryResponse(
            query_text=query_text,
            response_text=response_text,
            sources=[],
            timestamp=int(time.time())
        )
        return {
            "query_response": query_response,
            "retrieved_docs": [] if DEVELOPMENT_MODE else None
        }

    # Optional reranking logic
    if rerank:
        try:
            # Lazy import the reranker
            from services.reranker import Reranker, map_qdrant_rerank, map_rerank_qdrant

            # Map Qdrant results to rerank format
            mapped_results = map_qdrant_rerank(all_retrieved_docs)

            # Initialize and perform reranking
            reranker = Reranker(model_name="ms-marco-MultiBERT-L-12", cache_dir="/opt")
            reranked_docs = reranker.rerank(query_text, mapped_results)

            # Map the reranked results back to the original structure
            all_retrieved_docs = map_rerank_qdrant(reranked_docs, all_retrieved_docs)

        except Exception as e:
            logger.error(f"Reranker failed: {e}")
            return {
                "query_response": QueryResponse(
                    query_text=query_text,
                    response_text="An error occurred during reranking.",
                    sources=[],
                    timestamp=int(time.time())
                ),
                "retrieved_docs": [] if DEVELOPMENT_MODE else None
            }

    # Reconstruct sources for document chunks
    for doc in all_retrieved_docs:
        if not doc.get("source"):
            doc["source"] = reconstruct_source(doc.get("chunk_id", "Unknown Record"))

    # Generate LLM response
    response_text = await generate_llm_response(query_text, all_retrieved_docs, provider)

    # Create final response
    query_response = create_final_response(query_text, response_text, all_retrieved_docs)

    return {
        "query_response": query_response,
        "retrieved_docs": all_retrieved_docs if DEVELOPMENT_MODE else None,
        "debug_prompt": None
    }