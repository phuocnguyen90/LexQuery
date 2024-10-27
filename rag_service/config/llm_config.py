# src/config/llm_config.py

from pydantic import BaseModel, Field, validator
from typing import Optional

class BaseLLMConfig(BaseModel):
    provider: str = Field(..., description="The LLM provider (e.g., groq, openai, google_gemini, ollama)")

    @validator('provider')
    def validate_provider(cls, v):
        allowed = {'groq', 'openai', 'google_gemini', 'ollama'}
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of {allowed}")
        return v.lower()

class GroqLLMConfig(BaseModel):
    api_key: str = Field(..., description="API key for Groq")
    model_name: str = Field(..., description="Groq LLM model name")
    temperature: float = Field(..., description="Sampling temperature")
    max_output_tokens: int = Field(..., description="Maximum number of output tokens")
    embedding_model_name: Optional[str] = Field(None, description="Associated embedding model name if applicable")

class OpenAILLMConfig(BaseModel):
    api_key: str = Field(..., description="API key for OpenAI")
    model_name: str = Field(..., description="OpenAI LLM model name")
    temperature: float = Field(..., description="Sampling temperature")
    max_output_tokens: int = Field(..., description="Maximum number of output tokens")

class GoogleGeminiLLMConfig(BaseModel):
    api_key: str = Field(..., description="API key for Google Gemini")
    model_name: str = Field(..., description="Google Gemini LLM model name")
    temperature: float = Field(..., description="Sampling temperature")
    top_p: float = Field(..., description="Top-p sampling parameter")
    top_k: int = Field(..., description="Top-k sampling parameter")
    max_output_tokens: int = Field(..., description="Maximum number of output tokens")

class OllamaLLMConfig(BaseModel):
    api_key: str = Field(..., description="API key for Ollama")
    model_name: str = Field(..., description="Ollama LLM model name")
    model_path: str = Field(..., description="Path to the Ollama LLM model")
    temperature: float = Field(..., description="Sampling temperature")
    max_output_tokens: int = Field(..., description="Maximum number of output tokens")
    ollama_api_url: str = Field(..., description="URL for the Ollama LLM API")
