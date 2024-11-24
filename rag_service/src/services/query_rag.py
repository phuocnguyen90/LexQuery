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
    from get_embedding_function import get_embedding_function
except:
    from services.get_embedding_function import get_embedding_function

# Imports from shared_libs
from shared_libs.llm_providers import ProviderFactory
from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import AppConfigLoader, PromptConfigLoader

# Load configuration
config_loader = AppConfigLoader()
config = config_loader.config

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

DEVELOPMENT_MODE = True  # Enable this flag to include retrieved_docs in the response

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
    Generate the embedding vector for the query.
    """
    try:
        embedding_vector = await embedding_function(query_text)
        if embedding_vector is None:
            raise ValueError("Embedding vector is None.")
        return embedding_vector
    except Exception as e:
        logger.error(f"Failed to generate embedding for query '{query_text}': {e}")
        return None

async def retrieve_documents(embedding_vector: np.ndarray, top_k: int = 6) -> List[Dict]:
    """
    Retrieve similar documents using Qdrant.
    """
    from services.search_qdrant import search_qdrant
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
        paraphrase_prompt = f"Paraphrase the following query to improve search results:\n\n{query_text}"
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

    logger.debug(f"Message payload being sent: {json.dumps(message_payload, indent=2)}")

    # Generate response using the LLM provider
    try:
        response_text = await provider.send_single_message(message_payload=message_payload)
        return response_text
    except Exception as e:
        logger.error(f"Failed to generate a response using the provider for query: '{query_text}'. Error: {str(e)}")
        return "An error occurred while generating the answer."

def reconstruct_source(source_id: str) -> str:
    """
    Reconstruct a readable source string from a source_id.

    Rules:
    - Ignore 'ch' (chapter) if present.
    - 'art' is followed by a number without hyphen (e.g., 'art002' -> 'Điều 2').
    - 'cl_' is followed by a number (e.g., 'cl_12' -> 'khoản 12').
    - 'pt_' is followed by a label (e.g., 'pt_a' -> 'điểm a').

    :param source_id: The source ID to reconstruct.
    :return: A human-readable string describing the source.
    """
    try:
        # Initialize variables
        article = None
        clause = None
        point = None

        # Patterns to match 'art', 'cl_', and 'pt_'
        art_pattern = re.compile(r'art(\d+)', re.IGNORECASE)
        cl_pattern = re.compile(r'cl_(\d+)', re.IGNORECASE)
        pt_pattern = re.compile(r'pt_(\w+)', re.IGNORECASE)

        # Search for patterns
        art_match = art_pattern.search(source_id)
        cl_match = cl_pattern.search(source_id)
        pt_match = pt_pattern.search(source_id)

        # Extract base document (everything before the first '_')
        base_document = source_id.split('_')[0]

        # Extract article number
        if art_match:
            article_number = int(art_match.group(1))
            article = f"Điều {article_number}"

        # Extract clause number
        if cl_match:
            clause_number = int(cl_match.group(1))
            clause = f"khoản {clause_number}"

        # Extract point label
        if pt_match:
            point_label = pt_match.group(1)
            point = f"điểm {point_label}"

        # Assemble the reconstructed source
        reconstructed_parts = []
        if clause:
            reconstructed_parts.append(clause)
        if article:
            reconstructed_parts.append(article)
        if point:
            reconstructed_parts.append(point)

        # Combine parts with base document
        if reconstructed_parts:
            reconstructed_source = f"{', '.join(reconstructed_parts)} văn bản {base_document}"
        else:
            # If no article, clause, or point found, just return the base document
            reconstructed_source = f"văn bản {base_document}"

        return reconstructed_source

    except Exception as e:
        logger.error(f"Failed to reconstruct source from source_id '{source_id}': {e}")
        return "Unknown Source"


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
    conversation_history,
    provider: Optional[Any] = None,
    embedding_mode: Optional[str] = None,
    llm_provider_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query.
    """
    query_text = query_item.query_text

    # Initialize provider if not provided
    provider = provider or initialize_provider(llm_provider_name)

    # Determine the embedding mode
    current_embedding_mode = embedding_mode.lower() if embedding_mode else config.get('embedding', {}).get('mode', 'local').lower()

    # Get the embedding function based on the mode
    embedding_function = get_embedding_function()

    # Generate embedding vector for the query
    embedding_vector = await generate_embedding(query_text, embedding_function)

    if embedding_vector is None:
        # Return an error response
        return {
            "query_response": QueryResponse(
                query_text=query_text,
                response_text="An error occurred while creating embedding.",
                sources=[],
                timestamp=int(time.time())
            ),
            "retrieved_docs": [] if DEVELOPMENT_MODE else None
        }

    # Retrieve documents
    retrieved_docs = await retrieve_documents(embedding_vector, top_k=6)

    # If no documents found, try paraphrasing the query
    if not retrieved_docs:
        paraphrased_query = await paraphrase_query(query_text, provider)
        if paraphrased_query:
            # Generate embedding for paraphrased query
            embedding_vector = await generate_embedding(paraphrased_query, embedding_function)
            if embedding_vector:
                retrieved_docs = await retrieve_documents(embedding_vector, top_k=6)

    # If still no documents, return no data found
    if not retrieved_docs:
        logger.warning(f"No relevant documents found for query: '{query_text}'")
        response_text = "Không tìm thấy dữ liệu liên quan."
        sources = []
        query_response = QueryResponse(
            query_text=query_text,
            response_text=response_text,
            sources=sources,
            timestamp=int(time.time())
        )
        return {
            "query_response": query_response,
            "retrieved_docs": [] if DEVELOPMENT_MODE else None
        }

    # Reconstruct sources
    reconstruct_sources(retrieved_docs)

    # Rerank documents (optional)
    # retrieved_docs = await rerank_documents(retrieved_docs, query_text, provider)

    # Generate LLM response
    response_text = await generate_llm_response(query_text, retrieved_docs, provider)

    # Create final response
    query_response = create_final_response(query_text, response_text, retrieved_docs)

    # Return response
    return {
        "query_response": query_response,
        "retrieved_docs": retrieved_docs if DEVELOPMENT_MODE else None,
        "debug_prompt": None  # Include raw prompt if necessary
    }

