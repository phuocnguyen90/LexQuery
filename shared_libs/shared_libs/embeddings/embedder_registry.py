# shared_libs/embeddings/embedder_registry.py

from typing import Type, Dict
from .base_embedder import BaseEmbedder

class EmbedderRegistry:
    _registry: Dict[str, Type[BaseEmbedder]] = {}

    @classmethod
    def register(cls, provider_name: str, module_path: str, class_name: str):
        """
        Register a provider with its module path and class name.

        Args:
            provider_name (str): Name of the provider.
            module_path (str): Path to the module containing the provider class.
            class_name (str): Name of the provider class.
        """
        cls._registry[provider_name.lower()] = (module_path, class_name)

    @classmethod
    def get_embedder_class(cls, provider_name: str) -> Type[BaseEmbedder]:
        embedder_cls = cls._registry.get(provider_name.lower())
        if not embedder_cls:
            raise ValueError(f"No embedder registered for provider '{provider_name}'.")
        return embedder_cls
    
# EmbedderRegistry.register("cloud", "shared_libs.embeddings.cloud_embedder", "CloudEmbedder")
# EmbedderRegistry.register("local", "shared_libs.embeddings.local_embedder", "LocalEmbedder")
# EmbedderRegistry.register("docker", "shared_libs.embeddings.docker_embedder", "DockerEmbedder")
# EmbedderRegistry.register("bedrock", "shared_libs.embeddings.bedrock_embedder", "BedrockEmbedder")
# EmbedderRegistry.register("openai_embedding", "shared_libs.embeddings.openai_embedder", "OpenAIEmbedder")