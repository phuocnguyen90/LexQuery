# rag_service/src/services/get_embedding_function.py

import os
import asyncio
from typing import Callable, List, Optional, Awaitable
from shared_libs.utils.logger import Logger
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.embeddings.embedder_factory import EmbedderFactory

app_config=AppConfigLoader()
logger = Logger.get_logger(module_name=__name__)


# Load embedding configuration
embedding_config = EmbeddingConfig.get_embed_config(app_config)

# Retrieve EMBEDDING_MODE from environment variables
EMBEDDING_MODE = os.getenv('EMBEDDING_MODE', 'local').lower()

# Initialize the embedder using the EmbedderFactory
try:
    embedder = EmbedderFactory.create_embedder(EMBEDDING_MODE)
    logger.info(f"Initialized embedder for mode '{EMBEDDING_MODE}'.")
except Exception as e:
    logger.error(f"Failed to initialize embedder for mode '{EMBEDDING_MODE}': {e}")
    embedder = None

async def embed(query: str) -> Optional[List[float]]:
    """
    Asynchronous embedding function using the selected embedder.
    
    :param query: The input text to embed.
    :return: The embedding vector as a list of floats, or None if failed.
    """
    if not embedder:
        logger.error("Embedder is not initialized. Cannot generate embedding.")
        return None

    try:
        # Determine if the embedder's embed method is a coroutine
        if asyncio.iscoroutinefunction(embedder.embed):
            # If embed is an async function, await it directly
            embedding = await embedder.embed(query)
        else:
            # If embed is a synchronous function, run it in a thread pool
            loop = asyncio.get_running_loop()
            embedding = await loop.run_in_executor(None, embedder.embed, query)

        if embedding:
            logger.debug(f"Embedding generated for query: '{query}'")
            return embedding
        else:
            logger.error(f"No embedding generated for query: '{query}'")
            return None
    except Exception as e:
        logger.error(f"Embedding failed for query '{query}': {e}")
        return None

def get_embedding_function() -> Callable[[str], Awaitable[Optional[List[float]]]]:
    """
    Returns the appropriate embedding function based on the EMBEDDING_MODE environment variable.
    
    :return: An async function that takes a string and returns its embedding vector.
    """
    if not embedder:
        # Fallback embedding function that always returns None
        async def fallback_embed(query: str) -> Optional[List[float]]:
            logger.error("Embedder is not initialized. Cannot generate embedding.")
            return None
        return fallback_embed

    logger.info(f"Using '{EMBEDDING_MODE}' embedding function.")
    return embed
