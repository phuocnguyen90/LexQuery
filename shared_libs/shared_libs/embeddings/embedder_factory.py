# shared_libs/embeddings/embedder_factory.py

from typing import Dict, Type, Any
from .base_embedder import BaseEmbedder
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.config.provider_registry import ProviderRegistry
import importlib


class EmbedderFactory:
    def __init__(self, config: EmbeddingConfig):
        """
        Initialize EmbedderFactory with the embedding configuration.
        """
        if not isinstance(config, EmbeddingConfig):
            raise TypeError(f"Expected config to be an instance of EmbeddingConfig, got {type(config).__name__}")
        self.config = config
        self.dim = config.vector_dimension

    def load_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Load the configuration dictionary for a specific provider
        from the main EmbeddingConfig.
        """
        provider_name_key = provider_name.lower() # Standardize key for lookup

        # Assuming self.config.api_providers and self.config.library_providers are attributes
        # of EmbeddingConfig and are dictionaries.
        api_providers_config = getattr(self.config, 'api_providers', {})
        library_providers_config = getattr(self.config, 'library_providers', {})

        if not isinstance(api_providers_config, dict):
            raise TypeError(
                f"EmbeddingConfig.api_providers is expected to be a dict, "
                f"got {type(api_providers_config).__name__}."
            )
        if not isinstance(library_providers_config, dict):
            raise TypeError(
                f"EmbeddingConfig.library_providers is expected to be a dict, "
                f"got {type(library_providers_config).__name__}."
            )

        provider_specific_config = (
            api_providers_config.get(provider_name_key)
            or library_providers_config.get(provider_name_key)
        )
        
        if provider_specific_config is None:
            raise ValueError(
                f"No configuration found for provider '{provider_name_key}' in "
                f"EmbeddingConfig's api_providers or library_providers."
            )

        if not isinstance(provider_specific_config, dict):
            raise TypeError(
                f"Configuration for provider '{provider_name_key}' is not a dictionary, "
                f"got {type(provider_specific_config).__name__}."
            )

        return provider_specific_config

    
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
        try:
            specific_provider_config_dict = self.load_provider_config(provider_name)
        except (ValueError, TypeError) as e: # Catch errors from load_provider_config
            raise RuntimeError(f"Failed to load configuration for provider '{provider_name}': {e}") from e

        if not isinstance(specific_provider_config_dict, dict):
            raise TypeError(f"Expected a dictionary for provider configuration, got {type(specific_provider_config_dict).__name__}.")

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
        return EmbedderClass(specific_provider_config_dict)

