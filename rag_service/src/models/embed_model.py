# src/config/embedding_config.py

from pydantic import BaseModel, Field, validator
from typing import Optional

class BaseEmbeddingConfig(BaseModel):
    provider: str = Field(..., description="The embedding provider (e.g., local, docker, ec2, bedrock, groq_embedding, openai_embedding, google_gemini_embedding, ollama_embedding)")

    @validator('provider')
    def validate_provider(cls, v):
        allowed = {'local', 'docker', 'ec2', 'bedrock', 'groq_embedding', 'openai_embedding', 'google_gemini_embedding', 'ollama_embedding'}
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of {allowed}")
        return v.lower()

class LocalEmbeddingConfig(BaseModel):
    model_name: str = Field(..., description="Local model name")
    cache_dir: str = Field(..., description="Directory to cache local models")

class DockerEmbeddingConfig(BaseModel):
    service_url: str = Field(..., description="Docker service URL for embeddings")

class EC2EmbeddingConfig(BaseModel):
    service_url: str = Field(..., description="EC2 service URL for embeddings")

class BedrockEmbeddingConfig(BaseModel):
    model_id: str = Field(..., description="Amazon Bedrock model ID")
    region_name: str = Field(..., description="AWS region name")

class GroqEmbeddingConfig(BaseModel):
    api_key: str = Field(..., description="API key for Groq")
    model_name: str = Field(..., description="Groq embedding model name")

class OpenAIEmbeddingConfig(BaseModel):
    api_key: str = Field(..., description="API key for OpenAI")
    model_name: str = Field(..., description="OpenAI embedding model name")

class GoogleGeminiEmbeddingConfig(BaseModel):
    api_key: str = Field(..., description="API key for Google Gemini")
    model_name: str = Field(..., description="Google Gemini embedding model name")

class OllamaEmbeddingConfig(BaseModel):
    api_key: str = Field(..., description="API key for Ollama")
    model_name: str = Field(..., description="Ollama embedding model name")
    model_path: str = Field(..., description="Path to the Ollama embedding model")
    ollama_api_url: str = Field(..., description="URL for the Ollama embedding API")
