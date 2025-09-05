# shared_libs/config/provider_registry.py

from typing import Dict, Tuple, Type
import importlib
from pydantic import BaseModel

class ProviderRegistry:
    """
    Registry for managing embedding providers.
    Stores the module path and class name for each provider.
    """
    _registry: Dict[str, Tuple[str, str]] = {}

    @classmethod
    def register_provider(cls, provider_name: str, module_path: str, class_name: str):
        """
        Register a provider with its module path and class name.

        Args:
            provider_name (str): Name of the provider.
            module_path (str): Path to the module containing the provider class.
            class_name (str): Name of the provider class.
        """
        cls._registry[provider_name.lower()] = (module_path, class_name)

    @classmethod
    def get_provider_class(cls, provider_name: str) -> Type[BaseModel]:
        """
        Retrieve the provider class dynamically.

        Args:
            provider_name (str): Name of the provider.

        Returns:
            Type[BaseModel]: The class of the requested provider.

        Raises:
            ValueError: If the provider is not registered.
            ImportError: If the module or class cannot be loaded.
        """
        provider_name = provider_name.lower()
        if provider_name not in cls._registry:
            raise ValueError(f"Provider '{provider_name}' is not registered in the ProviderRegistry.")

        module_path, class_name = cls._registry[provider_name]
        try:
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                f"Failed to load provider class '{class_name}' from module '{module_path}': {e}"
            ) from e

# Register providers immediately upon module import
ProviderRegistry.register_provider("cloud", "shared_libs.embeddings.cloud_embedder", "CloudEmbedder")
ProviderRegistry.register_provider("local", "shared_libs.embeddings.local_embedder", "LocalEmbedder")
ProviderRegistry.register_provider(
    "local_gemma3",
    "shared_libs.embeddings.gemma_embedder",
    "GemmaLocalEmbedder",
)
ProviderRegistry.register_provider("docker", "shared_libs.embeddings.docker_embedder", "DockerEmbedder")
ProviderRegistry.register_provider("bedrock", "shared_libs.embeddings.bedrock_embedder", "BedrockEmbedder")
ProviderRegistry.register_provider("openai_embedding", "shared_libs.embeddings.openai_embedder", "OpenAIEmbedder")