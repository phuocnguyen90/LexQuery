# src/services/fe_embed.py

import os
import numpy as np
from typing import List
import fastembed  
from shared_libs.llm_providers import ProviderFactory  
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger

# Load configuration from shared_libs
config_loader = ConfigLoader()
logger = Logger.get_logger(module_name=__name__)

# Load embedding configuration from the global config
embedding_config = config_loader.get_config_value("embedding", {})
embedding_provider_name = embedding_config.get("provider_name", "local").lower()

# Define the model details
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CACHE_DIR = "/app/models"

# Ensure the cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

# Attempt to initialize the embedding provider
try:
    if embedding_provider_name != "local":
        embedding_provider = ProviderFactory.get_provider(
            name=embedding_provider_name,
            config=embedding_config,
            requirements=""
        )
        logger.info(f"Using '{embedding_provider_name}' as the embedding provider.")
    else:
        logger.info("Configured to use local embedding provider.")
        raise ValueError("Local embedding will be used.")  # Force fallback to local embedding
except Exception as e:
    # Fall back to FastEmbed with local files only
    logger.warning(
        f"Failed to initialize embedding provider '{embedding_provider_name}': {e}. "
        "Falling back to FastEmbed with local models."
    )
    try:
        embedding_provider = fastembed.TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=CACHE_DIR,
            local_files_only=True  # Ensure only local models are used
        )
        logger.info(f"FastEmbed initialized with model '{MODEL_NAME}' from '{CACHE_DIR}'.")
    except Exception as fe:
        logger.error(
            f"Failed to initialize FastEmbed with model '{MODEL_NAME}': {fe}. "
            "Ensure the model is downloaded in the cache directory."
        )
        raise

def fe_embed_text(text: str) -> List[float]:
    """
    Embed a single text using the selected embedding provider or FastEmbed as a fallback.

    :param text: A single text string to embed.
    :return: A list of floats representing the embedding vector.
    """
    try:
        # Determine the embedding provider
        if isinstance(embedding_provider, fastembed.TextEmbedding):
            logger.info("Embedding text using FastEmbed (local).")
            embedding_generator = embedding_provider.embed(text)
        else:
            logger.info(f"Embedding text with provider '{embedding_provider_name}'.")
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
