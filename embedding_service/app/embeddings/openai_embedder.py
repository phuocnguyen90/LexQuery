# WARNING: PLACE HOLDER ONLY. NOT WORKING
# app/embeddings/openai_embedder.py

import openai
from typing import List
from .base_embedder import BaseEmbedder
from config.embedding_config import OpenAIEmbeddingConfig
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
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI embed: {e}")
            return []

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of input texts, ensuring the total number of tokens does not exceed the model's limit.
        If the total number of tokens exceeds the limit, split the texts into smaller batches.
        """
        try:
            batches = self._split_into_batches(texts)
            all_embeddings = []

            for batch in batches:
                logger.debug(f"Generating embeddings for batch of {len(batch)} texts using OpenAI.")
                response = openai.Embedding.create(
                    input=batch,
                    model=self.model_name
                )
                embeddings = [item['embedding'] for item in response['data']]
                all_embeddings.extend(embeddings)

            return all_embeddings
        except openai.error.OpenAIError as e:
            logger.error(f"OpenAI API error during batch embed: {e}")
            return [[] for _ in texts]
        except Exception as e:
            logger.error(f"Unexpected error during OpenAI batch embed: {e}")
            return [[] for _ in texts]

    def _split_into_batches(self, texts: List[str]) -> List[List[str]]:
        """
        Split the list of texts into batches such that the total number of tokens in each batch does not exceed 8192 tokens.
        """
        max_tokens = 8192
        current_batch = []
        current_token_count = 0
        batches = []

        for text in texts:
            num_tokens = len(self.tokenizer.encode(text))

            if current_token_count + num_tokens > max_tokens:
                # Current batch exceeds the max token limit, finalize this batch and start a new one
                if current_batch:
                    batches.append(current_batch)
                current_batch = [text]
                current_token_count = num_tokens
            else:
                current_batch.append(text)
                current_token_count += num_tokens

        # Add the last batch if it's not empty
        if current_batch:
            batches.append(current_batch)

        return batches
