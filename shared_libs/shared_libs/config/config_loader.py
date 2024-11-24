# shared_libs\shared_libs\config\config_loader.py
from pathlib import Path
import yaml
import logging
import os
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings
from typing_extensions import Literal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from pathlib import Path

# Get the absolute path to the directory containing config_loader.py
CONFIG_DIR = Path(__file__).parent.resolve()
CONFIG_FILE_PATH = CONFIG_DIR / 'config.yaml'
DOTENV_FILE_PATH = CONFIG_DIR / '.env'
PROMPTS_FILE_PATH = CONFIG_DIR / 'prompts/prompts.yaml'
SCHEMAS_DIR_PATH = CONFIG_DIR / 'schemas/'


# Base Configuration Loader
class BaseConfigLoader:
    def __init__(self):
        pass

    def _load_environment_variables(self, dotenv_path: Optional[Path] = None):
        try:
            dotenv_file = dotenv_path or DOTENV_FILE_PATH
            if dotenv_file.exists():
                load_dotenv(dotenv_file)
                logger.debug(f"Loaded environment variables from '{dotenv_file}'.")
            else:
                logger.warning(f".env file not found at '{dotenv_file}'")
        except Exception as e:
            logger.error(f"Unexpected error loading environment variables: {e}")
            raise

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        try:
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return self._substitute_env_vars(data)
            else:
                logger.warning(f"YAML file not found at '{file_path}'")
                return {}
        except yaml.YAMLError as ye:
            logger.error(f"YAML parsing error in '{file_path}': {ye}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading YAML file '{file_path}': {e}")
            raise

    def _load_schemas(self, schemas_dir_path: Path) -> Dict[str, Any]:
        try:
            schemas = {}
            if schemas_dir_path.exists() and schemas_dir_path.is_dir():
                for schema_file in schemas_dir_path.glob("*.yaml"):
                    schema_name = schema_file.stem
                    schemas[schema_name] = self._load_yaml_file(schema_file)
                return schemas
            else:
                logger.warning(f"Schemas directory not found at '{schemas_dir_path}'")
                return {}
        except Exception as e:
            logger.error(f"Unexpected error loading schemas from '{schemas_dir_path}': {e}")
            raise

    def _substitute_env_vars(self, obj):
        if isinstance(obj, dict):
            return {k: self._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_env_vars(element) for element in obj]
        elif isinstance(obj, str):
            pattern = re.compile(r'\$\{([^}]+)\}')
            matches = pattern.findall(obj)
            for var in matches:
                env_value = os.getenv(var, "")
                if not env_value:
                    logger.warning(f"Environment variable '{var}' not found. Using empty string as a fallback.")
                obj = obj.replace(f"${{{var}}}", env_value)
            return obj
        else:
            return obj

# Application Configuration Loader
class AppConfigLoader(BaseConfigLoader):
    def __init__(self, config_path: Optional[str] = None, dotenv_path: Optional[str] = None):
        super().__init__()
        self._load_environment_variables(dotenv_path)
        self.config = self._load_yaml_file(config_path or CONFIG_FILE_PATH)

    def get(self, key: str, default=None):
        return self.config.get(key, default)

# Prompt Configuration Loader
class PromptConfigLoader(BaseConfigLoader):
    def __init__(self, prompts_path: Optional[str] = None):
        super().__init__()
        self.prompts = self._load_yaml_file(prompts_path or PROMPTS_FILE_PATH)

    def get_prompt(self, prompt_name: str) -> str:
        return self.prompts.get(prompt_name, "")

# Schema Configuration Loader
class SchemaConfigLoader(BaseConfigLoader):
    def __init__(self, schemas_path: Optional[str] = None):
        super().__init__()
        self.schemas = self._load_schemas(schemas_path or SCHEMAS_DIR_PATH)

    def get_schema(self, schema_name: str) -> Dict[str, Any]:
        return self.schemas.get(schema_name, {})

class LLMProviderConfigLoader:
    def __init__(self, config: Dict[str, Any]):
        self.llm_config = config.get('llm', {})

    def get_default_provider_name(self) -> str:
        # Returns the provider name specified in config, defaults to 'groq'
        return self.llm_config.get('provider', 'groq')

    def get_llm_provider_config(self, provider_name: str) -> Dict[str, Any]:
        # Returns the configuration for the specified provider
        return self.llm_config.get(provider_name, {})

    def get_default_provider_config(self) -> Dict[str, Any]:
        # Returns the configuration for the default provider
        provider_name = self.get_default_provider_name()
        config = self.get_llm_provider_config(provider_name)
        if not config:
            # Provide hardcoded default configuration if not found
            return self._get_hardcoded_default_config(provider_name)
        return config

    def _get_hardcoded_default_config(self, provider_name: str) -> Dict[str, Any]:
        # Returns hardcoded default configurations for known providers
        if provider_name == 'groq':
            return {
                'api_key': os.getenv('GROQ_API_KEY', ''),
                'llm_model_name': 'llama-3.1-8b-instant',
                'temperature': 0.7,
                'max_output_tokens': 2048,
            }
        elif provider_name == 'openai':
            return {
                'api_key': os.getenv('OPENAI_API_KEY', ''),
                'llm_model_name': 'gpt-3.5-turbo',
                'temperature': 0.7,
                'max_output_tokens': 2048,
            }
        # Add other providers as needed
        else:
            raise ValueError(f"No default configuration available for provider '{provider_name}'")


# Embedding Configurations using Pydantic
class BaseEmbeddingConfig(BaseSettings):
    provider: str = Field(..., description="Name of the embedding provider.")


class BedrockEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['bedrock'] = 'bedrock'
    embedding_model_name: str = Field(..., description="Bedrock model ID.")
    region_name: str = Field(..., description="AWS region name.")
    aws_access_key_id: SecretStr = Field(..., description="AWS access key ID.")
    aws_secret_access_key: SecretStr = Field(..., description="AWS secret access key.")

class LocalEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['local'] = 'local'
    embedding_model_name: str = Field(..., description="Local model name.")
    cache_dir: str = Field(..., description="Directory to cache models.")
    vector_dimension: Optional[int] = Field(None, description="Vector dimension for local models")

class OpenAIEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['openai_embedding'] = 'openai_embedding'
    embedding_model_name: str = Field(..., description="OpenAI model name.")
    openai_api_key: SecretStr = Field(..., description="OpenAI API key.")

class GoogleGeminiEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['google_gemini_embedding'] = 'google_gemini_embedding'
    embedding_model_name: str = Field(..., description="Google embedding model name.")
    google_gemini_api_key: SecretStr = Field(..., description="Google Gemini API key.")

class DockerEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['docker'] = 'docker'
    service_url: str = Field(..., description="Docker API service URL.")

class EC2EmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['ec2'] = 'ec2'
    service_url: str = Field(..., description="EC2 API service URL.")

class GenAIEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['genai'] = 'genai'
    library: str = Field(..., description="GenAI library path.")
    function_name: str = Field(..., description="Function name to call for embedding.")

class FastEmbedEmbeddingConfig(BaseEmbeddingConfig):
    provider: Literal['fastembed'] = 'fastembed'
    library_path: str = Field(..., description="FastEmbed library path.")
    function_name: str = Field(..., description="Function name to call for embedding.")

class EmbeddingConfig(BaseSettings):
    api_providers: Dict[str, BaseEmbeddingConfig] = Field(
        default_factory=dict,
        description="API-based embedding providers."
    )
    library_providers: Dict[str, BaseEmbeddingConfig] = Field(
        default_factory=dict,
        description="Library-based embedding providers."
    )


    @classmethod
    def from_config_loader(cls, config_loader: AppConfigLoader):
        """
        Parses the configuration using the AppConfigLoader to build embedding configurations.
        """
        embedding_section = config_loader.get('embedding', {})

        # Prepare containers for parsed configurations
        parsed_api_providers = {}
        parsed_library_providers = {}

        # Parse API providers
        api_providers = embedding_section.get('api_providers', {})
        for provider_name, provider_data in api_providers.items():
            if provider_name == "bedrock":
                parsed_api_providers[provider_name] = BedrockEmbeddingConfig(
                    embedding_model_name=provider_data['model_name'],
                    region_name=provider_data['region_name'],
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "")
                )
            elif provider_name == "openai_embedding":
                parsed_api_providers[provider_name] = OpenAIEmbeddingConfig(
                    embedding_model_name=provider_data['model_name'],
                    openai_api_key=os.getenv("OPENAI_API_KEY", "")
                )
            elif provider_name == "google_gemini_embedding":
                parsed_api_providers[provider_name] = GoogleGeminiEmbeddingConfig(
                    embedding_model_name=provider_data['model_name'],
                    google_gemini_api_key=os.getenv("GEMINI_API_KEY", "")
                )
            elif provider_name == "docker":
                parsed_api_providers[provider_name] = DockerEmbeddingConfig(
                    service_url=provider_data['service_url']
                )
            elif provider_name == "ec2":
                parsed_api_providers[provider_name] = EC2EmbeddingConfig(
                    service_url=provider_data['service_url']
                )
            # Add other API providers as needed

        # Parse library providers
        library_providers = embedding_section.get('library_providers', {})
        if 'local' in library_providers:
            local_config = library_providers['local']
            parsed_library_providers['local'] = LocalEmbeddingConfig(
                model_name=local_config['model_name'],
                cache_dir=local_config['cache_dir']
            )
        if 'genai' in library_providers:
            genai_config = library_providers['genai']
            parsed_library_providers['genai'] = GenAIEmbeddingConfig(
                library=genai_config['library'],
                function_name=genai_config['function_name']
            )
        if 'fastembed' in library_providers:
            fastembed_config = library_providers['fastembed']
            parsed_library_providers['fastembed'] = FastEmbedEmbeddingConfig(
                library_path=fastembed_config['library_path'],
                function_name=fastembed_config['function_name']
            )
        # Add other library providers as needed

        # Return the EmbeddingConfig instance
        return cls(api_providers=parsed_api_providers, library_providers=parsed_library_providers)

# Example Usage
if __name__ == "__main__":
    # Initialize the app config loader
    app_config_loader = AppConfigLoader()
    config = app_config_loader.config

    # Initialize the embedding config
    embedding_config = EmbeddingConfig.from_config_loader(app_config_loader)
    print(embedding_config)
