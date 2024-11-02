# WARNING: PLACE HOLDER ONLY. NOT WORKING
# app/embeddings/openai_embedder.py

import openai
from typing import List
from .base_embedder import BaseEmbedder
from shared_libs.config.embedding_config import OpenAIEmbeddingConfig
from shared_libs.utils.logger import Logger
import tiktoken

logger = Logger.get_logger(module_name=__name__)

class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, config: OpenAIEmbeddingConfig):
        """
        Initialize the OpenAIEmbedder with the specified configuration.

        :param config: OpenAIEmbeddingConfig instance containing necessary parameters.
        """
        self.api_key = config.openai_api_key.get_secret_value()
        self.model_name = config.model_name
        openai.api_key = self.api_key
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  
        logger.info(f"OpenAIEmbedder initialized with model '{self.model_name}'.")

    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for a single input text.
        """
        try:
            logger.debug(f"Generating embedding for text: '{text}' using OpenAI.")
            response = openai.Embedding.create(
                input=text,
                model=self.model_name
            )
            embedding = response['data'][0]['embedding']
            return embedding
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return []
        except AttributeError:
            logger.error("OpenAI API error attribute not found. Ensure that 'openai.error' is correct.")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI embed: {e}")
            return []

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using OpenAI embedding.

        :param texts: List of input text strings.
        :return: A list of lists, where each inner list represents the embedding for the corresponding input text.
        """
        try:
            logger.debug(f"Generating batch embeddings for {len(texts)} texts using OpenAI.")
            response = openai.Embedding.create(
                input=texts,
                model=self.model_name
            )
            embeddings = [item['embedding'] for item in response['data']]
            return embeddings
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            return [[] for _ in texts]
        except AttributeError:
            logger.error("OpenAI API error attribute not found. Ensure that 'openai.error' is correct.")
            return [[] for _ in texts]
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI batch embed: {e}")
            return [[] for _ in texts]
