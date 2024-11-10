from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import time
import sys
import os
import asyncio
from pydantic import BaseModel

# Imports from shared_libs
from shared_libs.llm_providers import ProviderFactory  
from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import AppConfigLoader, PromptConfigLoader
# Add parent directory to the sys.path to access shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    from services.search_qdrant import search_qdrant    # Absolute import for use in production
    from services.get_embedding_function import get_embedding_function
except ImportError:
    from search_qdrant import search_qdrant    # Relative import for direct script testing
    from get_embedding_function import get_embedding_function 

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

async def local_embed(query: str) -> Optional[List[float]]:
    """
    Temporary local embedding function for development purposes.
    Replace this with a proper embedding model as needed.
    """
    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    CACHE_DIR = "/app/models"
    try:
        import fastembed
        import numpy as np
        embedding_provider = fastembed.TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=CACHE_DIR,
            local_files_only=True  # Ensure only local models are used
        )
        embedding_generator = embedding_provider.embed(query)
        embeddings = list(embedding_generator)
        if not embeddings:
            logger.error(f"No embeddings returned for text '{query}'.")
            return []
        embedding = np.array(embeddings[0])  # Take the first embedding

        # Ensure that the embedding is a flat array
        if embedding.ndim != 1:
            logger.error(f"Embedding for text '{query}' is not a flat array. Got shape: {embedding.shape}")
            return []

        # Log embedding norm for debugging
        embedding_norm = np.linalg.norm(embedding)
        logger.debug(f"Embedding norm for text '{query}': {embedding_norm}")

        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to create embedding for the input: '{query}', error: {e}")
        return []

async def query_rag(
    query_item,
    provider: Optional[Any] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    embedding_mode: Optional[str] = None,
    llm_provider_name: Optional[str] = None  # New optional parameter
) -> QueryResponse:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query.

    :param query_item: An object containing the query text.
    :param provider: (Optional) An initialized LLM provider.
    :param conversation_history: (Optional) List of previous conversation messages.
    :param embedding_mode: (Optional) 'local' or 'api' to override the default embedding mode.
    :param llm_provider_name: (Optional) Name of the LLM provider to use if provider is not initialized.
    :return: QueryResponse containing the answer and sources.
    """
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
    if embedding_mode:
        current_embedding_mode = embedding_mode.lower()
        logger.debug(f"Overriding embedding mode to: {current_embedding_mode}")
    else:
        current_embedding_mode = config.get('embedding', {}).get('mode', 'local').lower()
        logger.debug(f"Using embedding mode from config: {current_embedding_mode}")

    # Get the embedding function based on the mode
    embedding_function = get_embedding_function()
    # Initialize the embedding vector
    embedding_vector = None

    if current_embedding_mode in ["local", "api"]:
        try:
            embedding_vector = await embedding_function(query_text)
            if embedding_vector is None:
                raise ValueError("Embedding vector is None.")
        except Exception as e:
            logger.error(f"Failed to generate embedding for query '{query_text}': {e}")
            return QueryResponse(
                query_text=query_text,
                response_text="An error occurred while creating embedding.",
                sources=[],
                timestamp=int(time.time())
            )
    else:
        logger.error(f"Unsupported embedding mode '{current_embedding_mode}'.")
        return QueryResponse(
            query_text=query_text,
            response_text="An error occurred while determining the embedding mode.",
            sources=[],
            timestamp=int(time.time())
        )

    # Proceed to retrieve similar documents using Qdrant
    logger.debug(f"Retrieving documents related to query: '{query_text}'")
    retrieved_docs = await search_qdrant(embedding_vector, top_k=3)
    if not retrieved_docs:
        logger.warning(f"No relevant documents found for query: '{query_text}'")
        response_text = "No relevant information found."
        sources = []
    else:
        # Combine retrieved documents to form context for LLM
        context = "\n\n---------------------------\n\n".join([
            f"Document ID: {doc['record_id']}\nSource: {doc['source']}\nContent: {doc['content']}"
            for doc in retrieved_docs if doc.get('content')
        ])
        logger.debug(f"Retrieved documents combined to form context for query: '{query_text}'")

        # Define the system prompt with clear citation instructions using the loaded prompt
        system_prompt = rag_prompt
        logger.debug(f"System prompt loaded for query: '{query_text}'")

        # Combine system prompt and user message to form the full prompt
        full_prompt = f"{system_prompt}\n\nUser Question: {query_text}\n\nRelated Answers:\n\n{context}"
        logger.debug(f"Full prompt created for query: '{query_text}'")

        # Generate response using the LLM provider
        try:
            logger.debug(f"Generating response using LLM provider")
            response_text = await provider.send_single_message(prompt=full_prompt)
        except Exception as e:
            logger.error(f"Failed to generate a response using the provider for query: '{query_text}'. Error: {str(e)}")
            response_text = "An error occurred while generating the answer."

        # Add citations to the response based on retrieved document IDs
        if retrieved_docs:
            citation_texts = [f"[Document ID: {doc['record_id']}]" for doc in retrieved_docs if doc.get('content')]
            if citation_texts:
                response_text += "\n\nReferences: " + ", ".join(citation_texts)

        # Extract sources from retrieved_docs
        sources = [doc['record_id'] for doc in retrieved_docs]

    # Create and return the QueryResponse
    response = QueryResponse(
        query_text=query_text,
        response_text=response_text,
        sources=sources,
        timestamp=int(time.time())
    )
    return response

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
    query_text = "Can I establish a joint-stock company with charter capital under 1 billion VND?"
    query_item = QueryModel(query_text=query_text)

    # Since query_rag is an async function, we need to await its result.
    response = await query_rag(query_item=query_item, llm_provider_name='groq')
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing: use asyncio.run to execute the async main function.
    asyncio.run(main())
