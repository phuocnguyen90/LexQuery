# shared_libs/embeddings/embedder_registry.py

from typing import Type, Dict
from .base_embedder import BaseEmbedder

class EmbedderRegistry:
    _registry: Dict[str, Type[BaseEmbedder]] = {}

    @classmethod
    def register(cls, provider_name: str):
        def decorator(embedder_cls: Type[BaseEmbedder]):
            cls._registry[provider_name.lower()] = embedder_cls
            return embedder_cls
        return decorator

    @classmethod
    def get_embedder_class(cls, provider_name: str) -> Type[BaseEmbedder]:
        embedder_cls = cls._registry.get(provider_name.lower())
        if not embedder_cls:
            raise ValueError(f"No embedder registered for provider '{provider_name}'.")
        return embedder_cls
