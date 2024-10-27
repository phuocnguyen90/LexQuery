# config/embedding_config.py

from pydantic import BaseSettings, Field
from typing import Optional, Dict
from typing_extensions import Literal

class BaseEmbeddingConfig(BaseSettings):
    provider: str = Field(..., description="Name of the embedding provider.")

    class Config:
        env_prefix = ''  # Adjust as needed

class BedrockEmbeddingConfig(BaseEmbeddingConfig):
    model_id: str = Field(..., description="Bedrock model ID.")
    region_name: str = Field(..., description="AWS region name.")

class LocalEmbeddingConfig(BaseEmbeddingConfig):
    model_name: str = Field(..., description="Local model name.")
    cache_dir: str = Field(..., description="Directory to cache models.")

# Define other provider-specific configs similarly...

class EmbeddingConfig(BaseSettings):
    api_providers: Dict[str, BaseEmbeddingConfig] = Field(
        default_factory=dict,
        description="API-based embedding providers."
    )
    library_providers: Dict[str, BaseEmbeddingConfig] = Field(
        default_factory=dict,
        description="Library-based embedding providers."
    )

    class Config:
        env_file = ".env"  # Specify your environment file if using
        # Optionally, include other configuration options
