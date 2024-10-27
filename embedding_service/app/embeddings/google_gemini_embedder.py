# WARNING: PLACE HOLDER ONLY. NOT WORKING

# src/embeddings/google_gemini_embedder.py

import google.generativeai as genai
from typing import List
from .base_embedder import BaseEmbedder
from embedding_service.app.config.embedding_config import GoogleGeminiEmbeddingConfig
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

class GoogleGeminiEmbedder(BaseEmbedder):
    def __init__(self, config: GoogleGeminiEmbeddingConfig):
        """
        Initialize the GoogleGeminiEmbedder with the specified configuration.

        :param config: GoogleGeminiEmbeddingConfig instance containing necessary parameters.
        """
        self.model = config.model_name
        self.task_type = config.task_type
        self.title = config.title
        self.api_key = config.api_key

        # Initialize the Google Generative AI library with the API key
        genai.configure(api_key=self.api_key)
        logger.info(f"GoogleGeminiEmbedder initialized with model '{self.model}'.")

    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text using Google Gemini's embed_content method.

        :param text: Input text string.
        :return: A list of floats representing the embedding.
        """
        try:
            logger.debug(f"Generating embedding for text: '{text}' using Google Gemini.")

            result = genai.embed_content(
                model=self.model,
                content=text,
                task_type=self.task_type,
                title=self.title
            )

            embedding = result.get('embedding', [])

            if not embedding:
                logger.error("No embedding received from Google Gemini embed_content.")
                return []

            logger.debug(f"Received embedding from Google Gemini: {embedding[:50]}... TRIMMED]")
            return embedding

        except Exception as e:
            logger.error(f"Error during Google Gemini embed: {e}")
            return []
