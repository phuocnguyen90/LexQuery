# shared_libs/config/qdrant_config.py

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_core.core_schema import FieldValidationInfo
from typing import Optional, Dict
from .app_config import AppConfigLoader
import os

class QdrantApiConfig(BaseModel):
    api_key: Optional[str] = Field(None, description="API key for Qdrant Cloud.")
    url: Optional[str] = Field(None, description="URL of the Qdrant server.")

    @field_validator('api_key', mode='before')

    def set_api_key(cls, v, info: FieldValidationInfo):
        return v or os.getenv("QDRANT_API_KEY")

    @field_validator('url', mode='before')

    def set_url(cls, v, info: FieldValidationInfo):
        return v or os.getenv("QDRANT_URL")

class QdrantConfig(BaseModel):
    api: QdrantApiConfig = Field(..., description="API configuration for Qdrant.")
    collection_names: Optional[Dict[str, str]] = Field(
        default_factory=lambda: {
            "qa_collection": "legal_qa",
            "doc_collection": "legal_doc"
        },
        description="Names of the Qdrant collections."
    )
    distance_metric: str = Field(
        "cosine",
        description="Distance metric to use for Qdrant vectors. Options: 'cosine', 'euclidean', 'dot'"
    )
    local: bool = Field(
        True,
        description="Whether to use a local Qdrant server."
    )

    @field_validator('distance_metric')
    def validate_distance_metric(cls, v):
        valid_metrics = {'cosine', 'euclidean', 'dot'}
        if v.lower() not in valid_metrics:
            raise ValueError(f"Invalid distance metric '{v}'. Valid options are {valid_metrics}.")
        return v.lower()
    
    @classmethod
    def from_config_loader(cls, config_loader: AppConfigLoader) -> "QdrantConfig":
        """
        Load QdrantConfig from a configuration loader.
        """
        config_data = config_loader.get("qdrant", {})
        return cls(**config_data)
