# src/embeddings/local_embedder.py

from typing import List, Dict, Any, Literal
from .base_embedder import BaseEmbedder
from .embedder_registry import EmbedderRegistry
from shared_libs.utils.logger import Logger
import fastembed
import numpy as np

logger = Logger.get_logger(module_name=__name__)

EmbedderRegistry.register("local", "shared_libs.embeddings.local_embedder", "LocalEmbedder")

class LocalEmbedder(BaseEmbedder):
    required_fields = ["model_name", "cache_dir", "vector_dimension"]

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the LocalEmbedder with fastembed client.

        Args:
            config (Dict[str, Any]): Configuration for the LocalEmbedder.
        """
        self.provider: Literal['local'] = 'local'

        # Validate required fields
        for field in self.required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in Local configuration.")

        self.model_name = config["model_name"]
        self.cache_dir = config["cache_dir"]
        self.vector_dimension = int(config["vector_dimension"])

        try:
            # Initialize fastembed client
            self.client = fastembed.TextEmbedding(model_name=self.model_name, cache_dir=self.cache_dir)
            logger.info(f"Successfully initialized fastembed model '{self.model_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize fastembed model '{self.model_name}': {e}")
            raise

    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text (str): The input text to embed.

        Returns:
            List[float]: The embedding vector for the input text.
        """
        try:
            # Use batch_embed with a single text for consistency
            embedding = self.batch_embed([text])[0]
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed text: {text}. Error: {e}")
            raise

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts (List[str]): A list of texts to embed.

        Returns:
            List[List[float]]: A list of embedding vectors, one for each text.
        """
        try:
            # Use fastembed to generate embeddings
            embeddings = self.client.embed(texts)
            # Convert to list of lists for compatibility
            return [embedding.tolist() for embedding in embeddings]
        except Exception as e:
            logger.error(f"Failed to embed batch of texts. Error: {e}")
            raise

    def vector_dimension(self) -> int:
        """
        Return the vector size for the model.

        Returns:
            int: The vector dimension for the embeddings.
        """
        return self.vector_dimension
