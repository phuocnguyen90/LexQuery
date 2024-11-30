# shared_libs/config/global_config.py

from pydantic import BaseModel, Field
from typing import Dict

class GlobalEmbeddingConfig(BaseModel):
    default_provider: str = Field(..., description="Default provider for embedding service.")
    mode: str = Field(..., description="Mode of interaction: 'local' or 'api'")
    api_service_url: str = Field(..., description="Global API URL for embedding service.")
    api_providers: Dict[str, Dict[str, str]]
    library_providers: Dict[str, Dict[str, str]]
