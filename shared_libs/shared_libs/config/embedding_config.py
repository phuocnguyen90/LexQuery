# shared_libs/config/embedding_config.py
from pydantic import BaseModel, Field
from typing import Dict, Union
from .provider_registry import ProviderRegistry

class EmbeddingConfig(BaseModel):
    default_provider: str = Field(..., description="Default provider for embedding service.")
    mode: str = Field(..., description="Mode of interaction: 'local' or 'api'")
    api_service_url: str = Field(..., description="Global API URL for embedding service.")

    # Providers
    api_providers: Dict[str, Dict[str, Union[str, int, float]]]
    library_providers: Dict[str, Dict[str, Union[str, int, float]]]

    model_config = {"arbitrary_types_allowed": True}  # To allow arbitrary types if needed


    @classmethod
    def from_config_loader(cls, config_loader) -> 'EmbeddingConfig':
        """
        Parses the configuration using the ConfigLoader to build embedding configurations.
        """
        embedding_section = config_loader.get('embedding', {})
        api_providers = embedding_section.get('api_providers', {})
        library_providers = embedding_section.get('library_providers', {})

        return cls(
            default_provider=embedding_section.get("default_provider", "local"),
            mode=embedding_section.get("mode", "local"),
            api_service_url=embedding_section.get("api_service_url", ""),
            api_providers=api_providers,
            library_providers=library_providers,
        )

    def load_provider_config(self, provider_name: str):
        """
        Dynamically load the configuration dictionary for a provider, 
        but do not instantiate the embedder class.
        """
        # Locate the provider's configuration in either API or library providers
        provider_config = (
            self.api_providers.get(provider_name)
            or self.library_providers.get(provider_name)
        )
        
        if not provider_config:
            raise ValueError(f"No configuration found for provider '{provider_name}'.")
        
        if not isinstance(provider_config, dict):
            raise TypeError(f"Expected a dictionary for provider configuration, got {type(provider_config).__name__}.")
        
        return provider_config


