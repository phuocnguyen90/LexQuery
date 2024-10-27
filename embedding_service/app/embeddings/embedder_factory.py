# src/embeddings/embedder_factory.py

from embedding_service.app.config.embedding_config import EmbeddingConfig, BaseEmbeddingConfig
from .base_embedder import BaseEmbedder
from .docker_embedder import DockerEmbedder
from .ec2_embedder import EC2Embedder
from .bedrock_embedder import BedrockEmbedder
from .openai_embedder import OpenAIEmbedder
from .google_gemini_embedder import GoogleGeminiEmbedder
from .local_embedder import LocalEmbedder
from shared_libs.utils.logger import Logger
from typing import Dict

logger = Logger.get_logger(module_name=__name__)


class EmbedderFactory:
    _embedders: Dict[str, BaseEmbedder] = {}

    @staticmethod
    def create_embedder(config: BaseEmbeddingConfig) -> BaseEmbedder:
        provider = config.provider.lower()

        if provider in EmbedderFactory._embedders:
            logger.debug(f"Using cached embedder for provider '{provider}'.")
            return EmbedderFactory._embedders[provider]

        if provider == "docker":
            embedder = DockerEmbedder(config)
        elif provider == "ec2":
            embedder = EC2Embedder(config)
        elif provider == "bedrock":
            embedder = BedrockEmbedder(config)
        elif provider == "openai_embedding":
            embedder = OpenAIEmbedder(config)
        elif provider == "google_gemini_embedding":
            embedder = GoogleGeminiEmbedder(config)
        elif provider == "local":
            embedder = LocalEmbedder(config)
        else:
            logger.error(f"Unsupported embedding provider: {provider}")
            raise ValueError(f"Unsupported embedding provider: {provider}")

        # Cache the embedder instance
        EmbedderFactory._embedders[provider] = embedder
        logger.info(f"Initialized and cached embedder for provider '{provider}'.")
        return embedder