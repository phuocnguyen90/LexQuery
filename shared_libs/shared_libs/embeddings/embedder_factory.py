# src/embeddings/embedder_factory.py

import importlib
from typing import Dict
from shared_libs.config.embedding_config import (
    EmbeddingConfig,
    BaseEmbeddingConfig
)
from .base_embedder import BaseEmbedder
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

class EmbedderFactory:
    _embedders: Dict[str, BaseEmbedder] = {}
    _embedding_config = EmbeddingConfig.from_config_loader()

    # Mapping of providers to their corresponding embedder module paths and class names
    _provider_mapping = {
        "bedrock": {
            "module_path": "bedrock_embedder",
            "class_name": "BedrockEmbedder"
        },
        "openai_embedding": {
            "module_path": "openai_embedder",
            "class_name": "OpenAIEmbedder"
        },
        "ec2": {
            "module_path": "ec2_embedder",
            "class_name": "EC2Embedder"
        },
        "google_gemini_embedding": {
            "module_path": "google_gemini_embedder",
            "class_name": "GoogleGeminiEmbedder"
        },
        "ollama_embedding": {
            "module_path": "ollama_embedder",
            "class_name": "OllamaEmbedder"
        },
        "local": {
            "module_path": "local_embedder",
            "class_name": "LocalEmbedder"
        },
        "docker": {
            "module_path": "docker_embedder",
            "class_name": "DockerEmbedder"
        },
        "genai": {
            "module_path": "genai_embedder",
            "class_name": "GenAIEmbedder"
        },
        "fastembed": {
            "module_path": "fastembed_embedder",
            "class_name": "FastEmbedEmbedder"
        },
        # Add other providers here as needed
    }

    @staticmethod
    def create_embedder(provider_name: str) -> BaseEmbedder:
        """
        Creates and returns an embedder instance based on the provider name.
        Caches the instance to avoid redundant initializations.
        
        Args:
            provider_name (str): The name of the embedding provider.
        
        Returns:
            BaseEmbedder: An instance of the requested embedder.
        
        Raises:
            ValueError: If the provider is unsupported or configuration is invalid.
            ImportError: If the embedder module or class cannot be imported.
        """
        provider = provider_name.lower()

        # Check if the embedder is already cached
        if provider in EmbedderFactory._embedders:
            logger.debug(f"Using cached embedder for provider '{provider}'.")
            return EmbedderFactory._embedders[provider]

        # Retrieve the provider's configuration
        provider_config: BaseEmbeddingConfig = None
        if provider in EmbedderFactory._embedding_config.api_providers:
            provider_config = EmbedderFactory._embedding_config.api_providers[provider]
            logger.debug(f"Provider '{provider}' found in API providers.")
        elif provider in EmbedderFactory._embedding_config.library_providers:
            provider_config = EmbedderFactory._embedding_config.library_providers[provider]
            logger.debug(f"Provider '{provider}' found in Library providers.")
        else:
            logger.error(f"Provider '{provider}' not found in configuration.")
            raise ValueError(f"Provider '{provider}' not found in configuration.")

        # Retrieve the embedder class details from the mapping
        provider_details = EmbedderFactory._provider_mapping.get(provider)
        if not provider_details:
            logger.error(f"No embedder mapping found for provider '{provider}'.")
            raise ValueError(f"No embedder mapping found for provider '{provider}'.")

        module_path = provider_details["module_path"]
        class_name = provider_details["class_name"]

        # Dynamically import the embedder module and class
        try:
            embedder_module = importlib.import_module(f".{module_path}", package=__package__)
            EmbedderClass = getattr(embedder_module, class_name)
            logger.debug(f"Successfully imported '{class_name}' from '{module_path}'.")
        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing '{class_name}' from '{module_path}': {e}")
            raise ImportError(f"Embedder class '{class_name}' not found in module '{module_path}'.") from e

        # Instantiate the embedder with the provider configuration
        try:
            embedder = EmbedderClass(provider_config)
            logger.info(f"Instantiated embedder '{class_name}' for provider '{provider}'.")
        except Exception as e:
            logger.error(f"Error instantiating embedder '{class_name}' for provider '{provider}': {e}")
            raise ValueError(f"Failed to instantiate embedder '{class_name}' for provider '{provider}': {e}") from e

        # Cache the embedder instance
        EmbedderFactory._embedders[provider] = embedder
        logger.info(f"Initialized and cached embedder for provider '{provider}'.")
        return embedder
