# WARNING: PLACE HOLDER ONLY. NOT WORKING
# src/embeddings/openai_embedder.py

import httpx
from typing import List
from .base_embedder import BaseEmbedder
from embedding_service.app.config.embedding_config import OpenAIEmbeddingConfig
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, config: OpenAIEmbeddingConfig):
        """
        Initialize the OpenAIEmbedder with the specified configuration.

        :param config: OpenAIEmbeddingConfig instance containing necessary parameters.
        """
        self.api_key = config.api_key
        self.model_name = config.model_name
        self.service_url = config.service_url  # Typically "https://api.openai.com/v1/embeddings"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info(f"OpenAIEmbedder initialized with model '{self.model_name}'.")

    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text using OpenAI's Embeddings API.

        :param text: Input text string.
        :return: A list of floats representing the embedding.
        """
        try:
            logger.debug(f"Sending embedding request to OpenAI for text: '{text}'.")

            payload = {
                "model": self.model_name,
                "input": text
            }

            response = httpx.post(
                self.service_url,
                json=payload,
                headers=self.headers,
                timeout=30.0
            )
            response.raise_for_status()

            data = response.json()
            embeddings = data.get("data", [])

            if not embeddings:
                logger.error("No embedding data received from OpenAI Embeddings API.")
                return []

            # Assuming the first item in 'data' contains the embedding
            embedding = embeddings[0].get("embedding", [])

            if not embedding:
                logger.error("No embedding found in OpenAI Embeddings API response.")
                return []

            logger.debug(f"Received embedding from OpenAI: {embedding[:50]}... TRIMMED]")
            return embedding

        except httpx.HTTPStatusError as http_err:
            logger.error(f"HTTP error during OpenAI embed: {http_err} - Response: {http_err.response.text}")
        except httpx.RequestError as req_err:
            logger.error(f"Request error during OpenAI embed: {req_err}")
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI embed: {e}")

        return []
