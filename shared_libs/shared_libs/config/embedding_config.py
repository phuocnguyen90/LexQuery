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
    def get_embed_config(cls, app_config) -> "EmbeddingConfig":
        emb = dict(app_config.config.get("embedding", {}) or {})

        # Apply environment overrides if present
        env_name = os.getenv("APP_ENV") or os.getenv("ENV")
        env_overrides = (emb.get("environments", {}) or {}).get(str(env_name), {}) if env_name else {}
        if env_overrides:
            # only override top-level keys we know about
            for k in ("default_provider", "api_service_url", "mode"):
                if k in env_overrides:
                    emb[k] = env_overrides[k]

        api_providers = emb.get("api_providers", {}) or {}
        library_providers = emb.get("library_providers", {}) or {}

        default_provider = emb.get("default_provider", "local")
        mode = emb.get("mode", "local")
        api_service_url = emb.get("api_service_url", "")

        # Determine active provider (env override wins)
        active_provider = os.getenv("ACTIVE_EMBEDDING_PROVIDER", default_provider)

        # Validate presence of default provider in its mode bucket
        if mode == "api":
            default_block = api_providers.get(default_provider)
            if default_block is None:
                raise ValueError(f"Default provider '{default_provider}' not found in api_providers.")
        else:
            default_block = library_providers.get(default_provider)
            if default_block is None:
                raise ValueError(f"Default provider '{default_provider}' not found in library_providers.")

        # Pick vector_dimension from active provider (prefer), else default provider
        active_block = api_providers.get(active_provider) or library_providers.get(active_provider)
        chosen_block = active_block or default_block
        if chosen_block is None:
            raise ValueError(f"No configuration found for provider '{active_provider}' or default '{default_provider}'.")

        vec_dim = chosen_block.get("vector_dimension")
        if vec_dim is None:
            raise ValueError(f"'vector_dimension' is not defined for provider '{active_provider}'.")

        return cls(
            default_provider=default_provider,
            mode=mode,
            api_service_url=api_service_url,
            api_providers=api_providers,
            library_providers=library_providers,
            vector_dimension=int(vec_dim),
        )

    def load_provider_config(self, provider_name: str):
        cfg = self.api_providers.get(provider_name) or self.library_providers.get(provider_name)
        if not cfg:
            raise ValueError(f"No configuration found for provider '{provider_name}'.")
        if not isinstance(cfg, dict):
            raise TypeError(f"Expected a dict for provider configuration, got {type(cfg).__name__}.")
        return cfg
    
    @property
    def active_provider(self) -> str:
        return os.getenv("ACTIVE_EMBEDDING_PROVIDER", self.default_provider)

    def get_vector_dimension(self) -> int:
        cfg = self.api_providers.get(self.active_provider) or self.library_providers.get(self.active_provider)
        if cfg is None:
            raise ValueError(f"No configuration found for provider '{self.active_provider}'.")
        dim = cfg.get("vector_dimension")
        if dim is None:
            raise ValueError(f"Vector dimension not defined for provider '{self.active_provider}'.")
        return int(dim)
