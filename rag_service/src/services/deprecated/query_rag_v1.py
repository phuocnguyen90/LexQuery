from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import time
import sys
import os
import asyncio
from pydantic import BaseModel

import os
import sys

# Ensure the parent directory is added to `sys.path` for consistent imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

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

import re
from typing import Optional

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


async def query_rag(
    query_item,
    conversation_history,
    provider: Optional[Any] = None,
    embedding_mode: Optional[str] = None,
    llm_provider_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query.

    :param query_item: An object containing the query text.
    :param provider: (Optional) An initialized LLM provider.
    :param embedding_mode: (Optional) 'local' or 'api' to override the default embedding mode.
    :param llm_provider_name: (Optional) Name of the LLM provider to use if provider is not initialized.
    :return: A dictionary containing the response and, if DEVELOPMENT_MODE is enabled, retrieved_docs.
    """
    from services.search_qdrant import search_qdrant
    from services.get_embedding_function import get_embedding_function

    query_text = query_item.query_text

    # Initialize provider if not provided
    if provider is None:
        if llm_provider_name:
            # Initialize provider using the provided name
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
            # Use default provider
            provider = llm_provider

    # Determine the embedding mode
    current_embedding_mode = embedding_mode.lower() if embedding_mode else config.get('embedding', {}).get('mode', 'local').lower()

    # Get the embedding function based on the mode
    embedding_function = get_embedding_function()
    embedding_vector = None

    if current_embedding_mode in ["local", "api"]:
        try:
            embedding_vector = await embedding_function(query_text)
            if embedding_vector is None:
                raise ValueError("Embedding vector is None.")
        except Exception as e:
            logger.error(f"Failed to generate embedding for query '{query_text}': {e}")
            return {
                "query_response": QueryResponse(
                    query_text=query_text,
                    response_text="An error occurred while creating embedding.",
                    sources=[],
                    timestamp=int(time.time())
                ),
                "retrieved_docs": [] if DEVELOPMENT_MODE else None
            }

    # Retrieve similar documents using Qdrant
    logger.debug(f"Retrieving documents related to query: '{query_text}'")
    retrieved_docs = await search_qdrant(embedding_vector, top_k=6)
    # Reconstruct sources for documents where source is None
    for doc in retrieved_docs:
        if not doc.get("source"):
            doc["source"] = reconstruct_source(doc.get("chunk_id", "Unknown Record"))

    if not retrieved_docs:
        logger.warning(f"No relevant documents found for query: '{query_text}'")
        response_text = "Không tìm thấy dữ liệu liên quan."
        sources = []
    else:
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

        # Combine system prompt and user message to form the full prompt
        full_prompt = f"{rag_prompt}\n\nUser Question: {query_text}\n\nRelated information:\n\n{context}"
        logger.debug(f"Full prompt created for query: '{query_text}'")

        # Generate response using the LLM provider
        try:
            response_text = await provider.send_single_message(prompt=full_prompt)
        except Exception as e:
            logger.error(f"Failed to generate a response using the provider for query: '{query_text}'. Error: {str(e)}")
            response_text = "An error occurred while generating the answer."

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

    # Inside query_rag, add the full_prompt to the returned dictionary
    return {
    "query_response": query_response,
    "retrieved_docs": retrieved_docs if DEVELOPMENT_MODE else None,
    "debug_prompt": full_prompt if DEVELOPMENT_MODE else None  # Include raw prompt for debugging
}



# For local testing
async def main():
    """
    For local testing.
    """
    logger.debug("Running example RAG call.")
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from models.query_model import QueryModel  
    query_text = "cổ đông gồm những ai"
    query_item = QueryModel(query_text=query_text)

    # Since query_rag is an async function, we need to await its result.
    response = await query_rag(query_item=query_item, llm_provider_name='groq')
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing: use asyncio.run to execute the async main function.
    asyncio.run(main())
