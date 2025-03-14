# shared_libs/config/embedding_config.py
from pydantic import BaseModel, Field
from typing import Dict, Union
from .provider_registry import ProviderRegistry
import os

class EmbeddingConfig(BaseModel):
    default_provider: str = Field(..., description="Default provider for embedding service.")
    mode: str = Field(..., description="Mode of interaction: 'local' or 'api'")
    api_service_url: str = Field(..., description="Global API URL for embedding service.")
    api_providers: Dict[str, Dict[str, Union[str, int, float]]]
    library_providers: Dict[str, Dict[str, Union[str, int, float]]]
    vector_dimension: int = Field(..., description="Vector dimension for the default provider.")

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def from_config_loader(cls, config_loader) -> 'EmbeddingConfig':
        """
        Parses the configuration using the ConfigLoader to build embedding configurations.
        """
        embedding_section = config_loader.get('embedding', {})
        api_providers = embedding_section.get('api_providers', {})
        library_providers = embedding_section.get('library_providers', {})

        default_provider = embedding_section.get("default_provider", "local")
        mode = embedding_section.get("mode", "local")
        
        # Determine which provider config to use based on the mode
        if mode == "api":
            provider_conf = api_providers.get(default_provider, {})
        else:
            provider_conf = library_providers.get(default_provider, {})

        vector_dimension = provider_conf.get("vector_dimension")
        if vector_dimension is None:
            raise ValueError(f"vector_dimension is not defined for the default provider '{default_provider}'.")

        return cls(
            default_provider=default_provider,
            mode=mode,
            api_service_url=embedding_section.get("api_service_url", ""),
            api_providers=api_providers,
            library_providers=library_providers,
            vector_dimension=vector_dimension
        )

    def load_provider_config(self, provider_name: str):
        """
        Dynamically load the configuration dictionary for a provider,
        but do not instantiate the embedder class.
        """
        provider_config = (
            self.api_providers.get(provider_name)
            or self.library_providers.get(provider_name)
        )
        
        if not provider_config:
            raise ValueError(f"No configuration found for provider '{provider_name}'.")
        
        if not isinstance(provider_config, dict):
            raise TypeError(f"Expected a dictionary for provider configuration, got {type(provider_config).__name__}.")
        
        return provider_config
    
    @property
    def active_provider(self) -> str:
        """
        Determine the active embedding provider.
        Checks for an environment variable 'ACTIVE_EMBEDDING_PROVIDER' and falls back to default_provider.
        """
        return os.getenv('ACTIVE_EMBEDDING_PROVIDER', self.default_provider)

    def get_vector_dimension(self) -> int:
        """
        Return the vector dimension for the active provider.
        """
        provider_config = (
            self.api_providers.get(self.active_provider)
            or self.library_providers.get(self.active_provider)
        )
        if provider_config is None:
            raise ValueError(f"No configuration found for provider '{self.active_provider}'.")
        dim = provider_config.get("vector_dimension")
        if dim is None:
            raise ValueError(f"Vector dimension not defined for provider '{self.active_provider}'.")
        return int(dim)
