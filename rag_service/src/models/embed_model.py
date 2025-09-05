# src/config/embedding_config.py

from pydantic import BaseModel, Field
from pydantic import field_validator
from typing import Optional, Literal

class BaseEmbeddingConfig(BaseModel):
    provider: str = Field(..., description="The embedding provider (e.g., local, docker, cloud, bedrock, groq_embedding, openai_embedding, google_gemini_embedding, ollama_embedding)")
    model_config = {"protected_namespaces": ()}
    @field_validator('provider')
    def validate_provider(cls, v):
        allowed = {'local', 'docker', 'cloud', 'bedrock', 'groq_embedding', 'openai_embedding', 'google_gemini_embedding', 'ollama_embedding'}
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of {allowed}")
        return v.lower()
    @field_validator("vector_dimension", mode="before", check_fields=False)
    def ensure_int(cls, v):
        """
        Ensure vector_dimension is always an integer.
        """
        if v is not None:
            return int(v)
        return v

class LocalEmbeddingConfig(BaseEmbeddingConfig):
    model_name: str = Field(..., description="Local model name")
    cache_dir: str = Field(..., description="Directory to cache local models")
    vector_dimension: Optional[int] = Field(None, description="Vector dimension for local models")

class DockerEmbeddingConfig(BaseEmbeddingConfig):
    service_url: str = Field(..., description="Docker service URL for embeddings")
    vector_dimension: int = Field(..., description="Vector dimension for the docker enpoint.")

class CloudEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal["cloud"] = "cloud"
    service_url: str = Field(..., description="Cloud service URL for embeddings")
    vector_dimension: int = Field(..., description="Vector dimension for the Cloud embedding model.")

class BedrockEmbeddingConfig(BaseEmbeddingConfig):
    model_id: str = Field(..., description="Amazon Bedrock model ID")
    region_name: str = Field(..., description="AWS region name")
    vector_dimension: int = Field(..., description="Vector dimension for the Bedrock embedding endpoint.")

class OpenAIEmbeddingConfig(BaseEmbeddingConfig):
    api_key: str = Field(..., description="API key for OpenAI")
    model_name: str = Field(..., description="OpenAI embedding model name")
    vector_dimension: int = Field(..., description="Vector dimension for the OpenAI embedding endpoint.")

class GoogleGeminiEmbeddingConfig(BaseEmbeddingConfig):
    api_key: str = Field(..., description="API key for Google Gemini")
    model_name: str = Field(..., description="Google Gemini embedding model name")
    vector_dimension: int = Field(..., description="Vector dimension for the Gemini embedding endpoint.")


class OllamaEmbeddingConfig(BaseEmbeddingConfig):
    api_key: str = Field(..., description="API key for Ollama")
    model_name: str = Field(..., description="Ollama embedding model name")
    model_path: str = Field(..., description="Path to the Ollama embedding model")
    ollama_api_url: str = Field(..., description="URL for the Ollama embedding API")
