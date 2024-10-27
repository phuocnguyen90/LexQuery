# config/embedding_config.py
# config/embedding_config.py

from pydantic import Field, SecretStr, ConfigDict
from pydantic_settings import BaseSettings
from typing import Dict, Optional
from typing_extensions import Literal
from shared_libs.config.config_loader import ConfigLoader
import os

# Base Configuration
class BaseEmbeddingConfig(BaseSettings):
    provider: str = Field(..., description="Name of the embedding provider.")

    model_config = ConfigDict(
        protected_namespaces=('settings_',)  # Redefine protected namespaces
    )

# Bedrock Configuration
class BedrockEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['bedrock'] = 'bedrock'
    model_id: str = Field(..., description="Bedrock model ID.")
    region_name: str = Field(..., description="AWS region name.")
    aws_access_key_id: SecretStr = Field(..., description="AWS access key ID.")
    aws_secret_access_key: SecretStr = Field(..., description="AWS secret access key.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

# Local Embedding Configuration
class LocalEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['local'] = 'local'
    model_name: str = Field(..., description="Local model name.")
    cache_dir: str = Field(..., description="Directory to cache models.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

# OpenAI Configuration
class OpenAIEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['openai_embedding'] = 'openai_embedding'
    model_name: str = Field(..., description="OpenAI model name.")
    openai_api_key: SecretStr = Field(..., description="OpenAI API key.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

# Google Gemini Configuration
class GoogleGeminiEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['google_gemini_embedding'] = 'google_gemini_embedding'
    model_name: str = Field(..., description="Google embedding model name.")
    google_gemini_api_key: SecretStr = Field(..., description="Google Gemini API key.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

# Docker Embedding Configuration
class DockerEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['docker'] = 'docker'
    service_url: str = Field(..., description="Docker API service URL.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

# EC2 Embedding Configuration
class EC2EmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['ec2'] = 'ec2'
    service_url: str = Field(..., description="EC2 API service URL.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

# GenAI Embedding Configuration
class GenAIEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['genai'] = 'genai'
    library: str = Field(..., description="GenAI library path.")
    function_name: str = Field(..., description="Function name to call for embedding.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

# FastEmbed Configuration
class FastEmbedEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['fastembed'] = 'fastembed'
    library_path: str = Field(..., description="FastEmbed library path.")
    function_name: str = Field(..., description="Function name to call for embedding.")
    model_config = ConfigDict(protected_namespaces=('settings_',))

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

    model_config = ConfigDict(protected_namespaces=('settings_',))

    @classmethod
    def from_config_loader(cls):
        """
        Parses the configuration using the ConfigLoader to build embedding configurations.
        """
        # Instantiate ConfigLoader and extract embedding configuration
        loader = ConfigLoader()
        embedding_section = loader.get_embedding_config()

        # Prepare containers for parsed configurations
        parsed_api_providers = {}
        parsed_library_providers = {}

        # Parse API providers from embedding_section
        api_providers = embedding_section.get('api_providers', {})

        for provider_name, provider_data in api_providers.items():
            if provider_name == "bedrock":
                parsed_api_providers[provider_name] = BedrockEmbeddingConfig(
                    provider='bedrock',
                    model_id=provider_data['model_id'],
                    region_name=provider_data['region_name'],
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "")
                )
            # Warning: DO NOT USE, INCOMPLETED
            elif provider_name == "openai_embedding":
                parsed_api_providers[provider_name] = OpenAIEmbeddingConfig(
                    provider='openai_embedding',
                    openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                    model_name=provider_data['model_name']
                )
            # Warning: DO NOT USE, INCOMPLETED    
            elif provider_name == "google_gemini_embedding":
                parsed_api_providers[provider_name] = GoogleGeminiEmbeddingConfig(
                    provider='google_gemini_embedding',
                    google_gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
                    model_name=provider_data['model_name']
                )
            # Warning: DO NOT USE, INCOMPLETED
            elif provider_name == "docker":
                parsed_api_providers[provider_name] = DockerEmbeddingConfig(
                    provider='docker',
                    service_url=provider_data['service_url']
                )
            # Warning: DO NOT USE, INCOMPLETED
            elif provider_name == "ec2":
                parsed_api_providers[provider_name] = EC2EmbeddingConfig(
                    provider='ec2',
                    service_url=provider_data['service_url']
                )

            

        # Parse library providers from embedding_section
        library_providers = embedding_section.get('library_providers', {})
        
        if 'local' in library_providers:
            local_config = library_providers['local']
            parsed_library_providers['local'] = LocalEmbeddingConfig(
                provider='local',
                model_name=local_config['model_name'],
                cache_dir=local_config['cache_dir']
            )

        if 'genai' in library_providers:
            genai_config = library_providers['genai']
            parsed_library_providers['genai'] = GenAIEmbeddingConfig(
                provider='genai',
                library=genai_config['library'],
                function_name=genai_config['function_name']
            )

        if 'fastembed' in library_providers:
            fastembed_config = library_providers['fastembed']
            parsed_library_providers['fastembed'] = FastEmbedEmbeddingConfig(
                provider='fastembed',
                library_path=fastembed_config['library_path'],
                function_name=fastembed_config['function_name']
            )

        # Return the EmbeddingConfig instance
        return cls(api_providers=parsed_api_providers, library_providers=parsed_library_providers)
