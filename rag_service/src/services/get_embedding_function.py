# rag_service/src/services/get_embedding_function.py

from typing import Callable, List, Optional, Awaitable
from shared_libs.utils.logger import Logger
import httpx
import asyncio
from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.embeddings.embedder_factory import EmbedderFactory

config=AppConfigLoader()
embedding_config=EmbeddingConfig.from_config_loader()

logger = Logger.get_logger(module_name=__name__)

async def local_embed(query: str) -> Optional[List[float]]:
    """
    Embedding function using the LocalEmbedder class.
    
    :param query: The input text to embed.
    :return: The embedding vector as a list of floats, or None if failed.
    """
    try:
        local_embedder = EmbedderFactory.create_embedder(embedding_config.library_providers['local'])

        loop = asyncio.get_running_loop()
        # Run the synchronous embed method in a thread pool executor
        embedding = await loop.run_in_executor(None, local_embedder.embed, query)
        if embedding:
            logger.debug(f"Local embedding generated for query: '{query}'")
            return embedding
        else:
            logger.error(f"No embedding generated for query: '{query}'")
            return None
    except Exception as e:
        logger.error(f"Local embedding failed for query '{query}': {e}")
        return None

async def api_embed(query: str, embedding_service_url: str) -> Optional[List[float]]:
    """
    Embedding function that uses an external embedding service via HTTP.
    
    :param query: The input text to embed.
    :param embedding_service_url: The URL of the embedding service API.
    :return: The embedding vector as a list of floats, or None if failed.
    """
    try:
        async with httpx.AsyncClient() as client:
            formatted_query = query.replace('\r\n', '\n').replace('\r', '\n')
            payload = {
            "texts": [formatted_query],
            "provider": "local",  # or "bedrock" based on configuration if needed
            "is_batch": False
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(embedding_service_url, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()
                embedding = data.get("embeddings")  # Assuming the API returns 'embeddings' key
                if embedding and isinstance(embedding, list) and len(embedding) > 0:
                    logger.debug(f"API embedding received for query: '{query}'")
                    return embedding[0]  # Return the first embedding if batch is false
                else:
                    logger.error(f"No embedding found in API response for query: '{query}'")
                    return None
    except httpx.HTTPError as e:
        logger.error(f"HTTP error when contacting embedding service: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error when contacting embedding service: {e}")
        return None

def get_embedding_function() -> Callable[[str], Awaitable[Optional[List[float]]]]:
    """
    Returns the appropriate embedding function based on configuration.
    
    :return: An async function that takes a string and returns its embedding vector.
    """
    EMBEDDING_MODE = config.get("embedding.mode", "local").lower()
    
    if EMBEDDING_MODE == "local":
        logger.info("Using local embedding function.")
        return local_embed
    elif EMBEDDING_MODE == "api":
        EMBEDDING_SERVICE_URL = config.get("embedding.api_service_url", "http://54.174.232.98:8000/embed")
        logger.info(f"Using API embedding function. Service URL: {EMBEDDING_SERVICE_URL}")
        
        async def embedding_api(query: str) -> Optional[List[float]]:
            return await api_embed(query, EMBEDDING_SERVICE_URL)
        
        return embedding_api
    else:
        logger.warning(f"Unknown EMBEDDING_MODE '{EMBEDDING_MODE}'. Defaulting to 'api'.")
        EMBEDDING_SERVICE_URL = config.get("embedding.api_service_url", "http://54.174.232.98:8000/embed")
        
        async def embedding_api_default(query: str) -> Optional[List[float]]:
            return await api_embed(query, EMBEDDING_SERVICE_URL)
        
        return embedding_api_default