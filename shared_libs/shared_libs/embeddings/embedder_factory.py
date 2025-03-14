# shared_libs/embeddings/embedder_factory.py

from typing import Dict, Type
from .base_embedder import BaseEmbedder
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.config.provider_registry import ProviderRegistry
import importlib


class EmbedderFactory:
    def __init__(self, config: EmbeddingConfig):
        """
        Initialize EmbedderFactory with the embedding configuration.
        """
        self.config = config
        self.dim = config.vector_dimension

    def load_provider_config(self, provider_name: str) -> dict:
        """
        Dynamically load the configuration dictionary for a provider.
        This method does NOT instantiate the provider class.
        """
        # Locate the provider's configuration in either API or library providers
        provider_config = (
            self.api_providers.get(provider_name)
            or self.library_providers.get(provider_name)
        )
        if not provider_config:
            raise ValueError(f"No configuration found for provider '{provider_name}'.")

        # Ensure the result is a dictionary
        if not isinstance(provider_config, dict):
            raise TypeError(f"Expected a dictionary for provider configuration, got {type(provider_config).__name__}.")

        return provider_config

    
    def create_embedder(self, provider_name: str) -> BaseEmbedder:
        """
        Dynamically load the embedder class and create an instance based on the provider name.

        Args:
            provider_name (str): The name of the embedding provider.

        Returns:
            BaseEmbedder: An instance of the dynamically loaded embedder class.
        """
        provider_name = provider_name.lower()

        # Check if the provider is registered
        if provider_name not in ProviderRegistry._registry:
            raise ValueError(f"Provider '{provider_name}' is not registered in the ProviderRegistry.")

        # Get the provider configuration
        provider_config = self.config.load_provider_config(provider_name)
        if not isinstance(provider_config, dict):
            raise TypeError(f"Expected a dictionary for provider configuration, got {type(provider_config).__name__}.")

        # Dynamically load the embedder class
        module_path, class_name = ProviderRegistry._registry[provider_name]
        try:
            module = importlib.import_module(module_path)
            EmbedderClass = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Failed to load embedder class '{class_name}' from module '{module_path}': {e}"
            ) from e

        # Create and return the embedder instance
        return EmbedderClass(provider_config)

