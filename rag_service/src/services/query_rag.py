# rag_service/src/services/query_rag.py
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
EMBEDDING_MODE = os.getenv('EMBEDDING_MODE','local')
embedding_config = EmbeddingConfig.from_config_loader(config_loader)
factory = EmbedderFactory(embedding_config)
embedding_function = factory.create_embedder(EMBEDDING_MODE)  

# Configure logging (using our custom logger)
logger = Logger.get_logger(module_name=__name__)

prompt_config = PromptConfigLoader()

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
        # Log raw prompt for paraphrasing
        logger.raw(f"Paraphrase prompt sent: {paraphrase_prompt}")
        paraphrased_query = await provider.send_single_message(prompt=paraphrase_prompt)
        # Log raw LLM response for paraphrasing
        logger.raw(f"Paraphrase response received: {paraphrased_query}")
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
        prompt = (f"On a scale of 1 to 10, how relevant is the following document to the query?\n\n"
                  f"Query: {query_text}\n\nDocument: {doc_content}\n\nRelevance Score (1-10):")
        # Log raw prompt for relevance scoring
        logger.raw(f"Relevance score prompt sent: {prompt}")
        response = await provider.send_single_message(prompt=prompt)
        # Log raw response for relevance scoring
        logger.raw(f"Relevance score raw response received: {response}")
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

async def extract_keywords(query_text: str, provider: Any, top_k: int = 10) -> List[str]:
    """
    Extract top_k keywords from the user query using the LLM.
    """
    if not query_text:
        logger.error("No query text provided for keyword extraction.")
        return []

    if provider is None:
        logger.error("No LLM provider instance provided.")
        return []

    try:
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
        logger.raw(f"Keyword extraction prompt sent: {prompt}")
        response = await provider.send_single_message(prompt=prompt)
        logger.raw(f"Keyword extraction raw response received: {response}")
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
                    logger.raw(f"Extracted Keywords: {keywords}")
                    return keywords
                else:
                    logger.warning("The 'keywords' field is invalid or empty.")
                    return []
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse JSON from LLM response: {je}")
                return []
        else:
            logger.warning("No valid JSON found in the LLM response. Falling back to plain text parsing.")
            list_match = re.findall(r'\b\w+\b', response)
            if list_match:
                keywords = list_match[:top_k]
                logger.debug(f"Extracted Keywords from plain text: {keywords}")
                logger.raw(f"Extracted Keywords from plain text: {keywords}")
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

    MAX_CONTEXT_LENGTH = 8000  # Adjust as needed
    if len(context) > MAX_CONTEXT_LENGTH:
        logger.warning("Context is too long, truncating.")
        context = context[:MAX_CONTEXT_LENGTH]

    messages = [
        {
            "role": "system",
            "content": rag_prompt
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

    message_payload = {
        "messages": messages
    }
    # Log the raw payload being sent to the LLM
    import json
    logger.raw(f"LLM message payload sent: {json.dumps(message_payload, indent=2)}")
    try:
        response_text = await provider.send_single_message(message_payload=message_payload)
        logger.raw(f"LLM raw response received: {response_text}")
        return response_text
    except Exception as e:
        logger.error(f"Failed to generate a response using the provider for query: '{query_text}'. Error: {str(e)}")
        return "An error occurred while generating the answer."

def create_final_response(query_text: str, response_text: str, retrieved_docs: List[Dict]) -> QueryResponse:
    """
    Create the final QueryResponse object.
    """
    if retrieved_docs:
        citation_texts = [f"[Record ID: {doc['record_id']}]" for doc in retrieved_docs if doc.get('content')]
        if citation_texts:
            response_text += "\n\nReferences: " + ", ".join(citation_texts)
    sources = [doc['record_id'] for doc in retrieved_docs]
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
    keyword_gen: bool = False,
) -> Dict[str, Any]:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query.
    """
    query_text = query_item.query_text

    provider = provider or initialize_provider(llm_provider_name)

    current_embedding_mode = embedding_mode.lower() if embedding_mode else config.get('embedding', {}).get('mode', 'local').lower()

    embedding_config = EmbeddingConfig.from_config_loader(config_loader)
    factory = EmbedderFactory(embedding_config)

    if current_embedding_mode == "api":
        embedding_function = factory.create_embedder('ec2')
    elif current_embedding_mode == "local":
        embedding_function = factory.create_embedder('local')
    else:
        raise ValueError(f"Unsupported embedding mode: {current_embedding_mode}")

    embedding_vector = await generate_embedding(query_text, embedding_function)
    if embedding_vector is None:
        return {
            "query_response": QueryResponse(
                query_text=query_text,
                response_text="An error occurred while creating embedding.",
                sources=[],
                timestamp=int(time.time())
            ).model_dump(),
            "retrieved_docs": [] if DEVELOPMENT_MODE else None
        }

    QA_COLLECTION_NAME = os.getenv("QA_COLLECTION_NAME", "legal_qa")
    DOC_COLLECTION_NAME = os.getenv("DOC_COLLECTION_NAME", "legal_doc")
    all_retrieved_docs = []

    # Initialize extra logging variables
    extracted_keywords = []
    rerank_applied = False

    if keyword_gen:
        for attempt in range(2):
            try:
                logger.debug(f"Attempt {attempt + 1}: Extracting keywords for query: {query_text}")
                keywords = await extract_keywords(query_text, provider, top_k=10)
                if isinstance(keywords, list) and len(keywords) > 0:
                    logger.debug(f"Keywords extracted: {keywords}")
                    logger.raw(f"Keywords extracted: {keywords}")
                    extracted_keywords = keywords
                    qa_docs = await advanced_qdrant_search(
                        embedding_vector, keywords, collection_name=QA_COLLECTION_NAME, top_k=3
                    )
                    doc_chunks = await advanced_qdrant_search(
                        embedding_vector, keywords, collection_name=DOC_COLLECTION_NAME, top_k=6
                    )
                    all_retrieved_docs = qa_docs + doc_chunks
                    break
                else:
                    logger.warning("Keyword extraction returned an invalid or empty list.")
            except Exception as e:
                logger.error(f"Error during keyword extraction: {e}")

        if not all_retrieved_docs:
            logger.warning("Falling back to normal search_qdrant due to keyword generation failure.")
            qa_docs = await search_qdrant(embedding_vector, collection_name=QA_COLLECTION_NAME, top_k=3)
            doc_chunks = await search_qdrant(embedding_vector, collection_name=DOC_COLLECTION_NAME, top_k=6)
            all_retrieved_docs = qa_docs + doc_chunks
    else:
        qa_docs = await search_qdrant(embedding_vector, collection_name=QA_COLLECTION_NAME, top_k=3)
        doc_chunks = await search_qdrant(embedding_vector, collection_name=DOC_COLLECTION_NAME, top_k=6)
        all_retrieved_docs = qa_docs + doc_chunks

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
            "query_response": query_response.model_dump(),
            "retrieved_docs": [] if DEVELOPMENT_MODE else None,
            "keywords": extracted_keywords,
            "rerank_applied": False,
        }

    if rerank:
        try:
            from services.reranker import Reranker, map_qdrant_rerank, map_rerank_qdrant
            mapped_results = map_qdrant_rerank(all_retrieved_docs)
            reranker = Reranker(model_name="ms-marco-MultiBERT-L-12", cache_dir="/opt")
            reranked_docs = reranker.rerank(query_text, mapped_results)
            all_retrieved_docs = map_rerank_qdrant(reranked_docs, all_retrieved_docs)
            rerank_applied = True
            logger.raw("Reranking applied successfully.")
        except Exception as e:
            logger.error(f"Reranker failed: {e}")
            return {
                "query_response": QueryResponse(
                    query_text=query_text,
                    response_text="An error occurred during reranking.",
                    sources=[],
                    timestamp=int(time.time())
                ).model_dump(),
                "retrieved_docs": [] if DEVELOPMENT_MODE else None,
                "keywords": extracted_keywords,
                "rerank_applied": False,
            }

    for doc in all_retrieved_docs:
        if not doc.get("source"):
            doc["source"] = reconstruct_source(doc.get("chunk_id", "Unknown Record"))

    response_text = await generate_llm_response(query_text, all_retrieved_docs, provider)
    query_response = create_final_response(query_text, response_text, all_retrieved_docs)

    return {
        "query_response": query_response.model_dump(),
        "retrieved_docs": all_retrieved_docs if DEVELOPMENT_MODE else None,
        "debug_prompt": None,
        "keywords": extracted_keywords,
        "rerank_applied": rerank_applied,
    }
