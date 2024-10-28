# src/embeddings/bedrock_embedder.py

import json
import boto3
from botocore.exceptions import ClientError
from typing import List, Optional
from .base_embedder import BaseEmbedder
from shared_libs.config.embedding_config import BedrockEmbeddingConfig
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

class BedrockEmbedder(BaseEmbedder):
    def __init__(self, config: BedrockEmbeddingConfig):
        """
        Initialize the BedrockEmbedder with the specified configuration.

        :param config: BedrockEmbeddingConfig instance containing necessary parameters.
        """
        self.model_id = config.model_id
        self.region_name = config.region_name

        # Initialize the Bedrock client with credentials
        try:
            self.bedrock_client = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region_name,
                aws_access_key_id=config.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=config.aws_secret_access_key.get_secret_value()
            )
            logger.info(f"BedrockEmbedder initialized with model ID '{self.model_id}' in region '{self.region_name}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise

    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for the given text using Amazon Titan Embeddings G1 - Text model.

        :param text: Input text string.
        :return: A list of floats representing the embedding.
        """
        try:
            logger.debug(f"Generating embedding for text: '{text}' using Bedrock model '{self.model_id}'.")

            # Create request body
            body = json.dumps({
                "inputText": text
            })

            # Invoke the Bedrock model
            response = self.bedrock_client.invoke_model(
                body=body,
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json"
            )

            # Parse the response
            response_body = json.loads(response.get('body').read())
            embedding = response_body.get('embedding', [])

            if not embedding:
                logger.error("No embedding received from Bedrock Embeddings API.")
                return []

            logger.debug(f"Received embedding from Bedrock: {embedding[:50]}... TRIMMED]")
            return embedding

        except ClientError as e:
            error_message = e.response["Error"]["Message"]
            logger.error(f"AWS ClientError during Bedrock embed: {error_message}")
        except Exception as e:
            logger.error(f"Unexpected error during Bedrock embed: {e}")

        return []
    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts using Amazon Titan Embeddings G1 - Text model.

        :param texts: List of input text strings.
        :return: A list of lists, where each inner list represents the embedding for the corresponding input text.
        """
        embeddings = []
        for text in texts:
            embedding = self.embed(text)
            embeddings.append(embedding)
        return embeddings
