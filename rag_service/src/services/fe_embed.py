# src/services/fe_embed.py

import logging
import numpy as np
from typing import List
from shared_libs.providers import get_embedding_provider
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger

# Load configuration from shared_libs
config = ConfigLoader.load_config()

# Configure logging using Logger from shared_libs
logger = Logger.get_logger(__name__)

# Get embedding provider instance (FastEmbed or similar)
embedding_config = config.get("embedding", {})
embedding_provider = get_embedding_provider(embedding_config)

def fe_embed_text(text: str) -> List[float]:
    """
    Embed a single text using an embedding provider (e.g., FastEmbed).

    :param text: A single text string to embed.
    :return: A list of floats representing the embedding vector.
    """
    try:
        # Obtain the embedding generator from the provider
        embedding_generator = embedding_provider.embed(text)
        
        # Convert the generator to a list and then to a numpy array
        embeddings = list(embedding_generator)
        if not embeddings:
            logger.error(f"No embeddings returned for text '{text}'.")
            return []

        embedding = np.array(embeddings)

        # Handle 2D arrays with a single embedding vector
        if embedding.ndim == 2 and embedding.shape[0] == 1:
            embedding = embedding[0]

        # Ensure that the embedding is a flat array
        if embedding.ndim != 1:
            logger.error(f"Embedding for text '{text}' is not a flat array. Got shape: {embedding.shape}")
            return []

        # Log embedding norm for debugging
        embedding_norm = np.linalg.norm(embedding)
        logger.debug(f"Embedding norm for text '{text}': {embedding_norm}")

        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to create embedding for the input: '{text}', error: {e}")
        return []
