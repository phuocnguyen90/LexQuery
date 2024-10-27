# WARNING: PLACE HOLDER ONLY. NOT WORKING

# app/embeddings/google_gemini_embedder.py

import google.generativeai as genai
from typing import List
from .base_embedder import BaseEmbedder
from config.embedding_config import GoogleGeminiEmbeddingConfig
from shared_libs.utils.logger import Logger
import requests

logger = Logger.get_logger(module_name=__name__)

class GoogleGeminiEmbedder(BaseEmbedder):
    def __init__(self, config: GoogleGeminiEmbeddingConfig):
        """
        Initialize the GoogleGeminiEmbedder with the specified configuration.

        :param config: GoogleGeminiEmbeddingConfig instance containing necessary parameters.
        """
        self.api_key = config.google_gemini_api_key.get_secret_value()
        self.endpoint = "https://gemini.googleapis.com/v1/embeddings"  
        logger.info("GoogleGeminiEmbedder initialized with provided credentials.")


    def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate an embedding for the given text using Google Gemini's embed_content method.

        :param text: Input text string.
        :return: A list of floats representing the embedding.
        """
        embeddings = []
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        for text in texts:
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
                    logger.error("No embedding received from Google Gemini Embeddings API.")
                    embeddings.append([])
                else:
                    embeddings.append(embedding)
            except requests.exceptions.RequestException as e:
                logger.error(f"Google Gemini API request error: {e}")
                embeddings.append([])
            except Exception as e:
                logger.error(f"Unexpected error during Google Gemini embed: {e}")
                embeddings.append([])
        return embeddings
