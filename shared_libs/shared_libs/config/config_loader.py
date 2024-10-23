# shared_libs/config/config_loader.py

from pathlib import Path
import yaml
import logging
import os
import re
from dotenv import load_dotenv
from shared_libs.utils.aws_auth_validation import validate_dynamodb, validate_s3


class ConfigLoader:
    _instance = None

    def __new__(cls, config_path=None, dotenv_path=None, prompts_path=None, schemas_path=None):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)

            # Default paths if not provided
            config_path = config_path or os.environ.get('CONFIG_PATH', 'config/config.yaml')
            dotenv_path = dotenv_path or os.environ.get('DOTENV_PATH', 'config/.env')
            prompts_path = prompts_path or os.environ.get('PROMPTS_PATH', 'prompts/prompts.yaml')
            schemas_path = schemas_path or os.environ.get('SCHEMAS_PATH', 'schemas/')


            # Load environment variables, configuration, prompts, and schemas
            cls._instance._load_environment_variables(dotenv_path)
            cls._instance._load_config(config_path)
            cls._instance._load_prompts(prompts_path)
            cls._instance._load_schemas(schemas_path)
            
            DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"
            if DEVELOPMENT_MODE:
                pass
            else:                
                # Validate AWS resources before proceeding with the rest of the configuration
                validate_dynamodb(os.getenv('CACHE_TABLE_NAME', 'CacheTable'))
                validate_dynamodb(os.getenv('LOG_TABLE_NAME', 'LogTable'))
                validate_s3()
        return cls._instance

    def _load_environment_variables(self, dotenv_relative_path):
        try:
            base_dir = Path(__file__).resolve().parent.parent
            dotenv_path = base_dir / dotenv_relative_path

            # Load environment variables if .env exists
            if dotenv_path.exists():
                load_dotenv(dotenv_path)
                logging.debug(f"Loaded environment variables from '{dotenv_path}'.")
                logging.debug(f"Environment variables loaded: {dict(os.environ)}")

            else:
                logging.warning(f".env file not found at '{dotenv_path}'")
        except Exception as e:
            logging.error(f"Unexpected error loading environment variables: {e}")
            raise

    def _load_config(self, config_relative_path):
        try:
            # Resolve the absolute path dynamically using pathlib
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / config_relative_path

            # Load YAML configuration file
            with config_path.open('r', encoding='utf-8') as file:
                config = yaml.safe_load(file)

            # Substitute environment variables in the configuration
            self.config = self._substitute_env_vars(config)
            logging.debug(f"Configuration loaded successfully from '{config_path}'.")

        except FileNotFoundError:
            logging.error(f"Configuration file '{config_path}' not found.")
            raise
        except yaml.YAMLError as ye:
            logging.error(f"YAML parsing error in '{config_path}': {ye}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error loading configuration: {e}")
            raise

    def _load_prompts(self, prompts_relative_path):
        try:
            # Resolve the absolute path dynamically using pathlib
            base_dir = Path(__file__).resolve().parent.parent
            prompts_path = base_dir / prompts_relative_path

            # Load YAML prompts file
            with prompts_path.open('r', encoding='utf-8') as file:
                prompts = yaml.safe_load(file)

            # Store prompts as part of the instance
            self.prompts = self._substitute_env_vars(prompts)
            logging.debug(f"Prompts loaded successfully from '{prompts_path}'.")

        except FileNotFoundError:
            logging.error(f"Prompts file '{prompts_path}' not found.")
            raise
        except yaml.YAMLError as ye:
            logging.error(f"YAML parsing error in '{prompts_path}': {ye}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error loading prompts: {e}")
            raise

    def _load_schemas(self, schemas_relative_path):
        try:
            base_dir = Path(__file__).resolve().parent.parent
            schemas_dir = base_dir / schemas_relative_path

            # Load all YAML files from the schemas directory
            schemas = {}
            for schema_file in schemas_dir.glob("*.yaml"):
                with schema_file.open('r', encoding='utf-8') as file:
                    schema_content = yaml.safe_load(file)
                    schema_name = schema_file.stem
                    schemas[schema_name] = self._substitute_env_vars(schema_content)

            # Store schemas as part of the instance
            self.schemas = schemas
            logging.debug(f"Schemas loaded successfully from '{schemas_dir}'.")

        except FileNotFoundError:
            logging.error(f"Schemas directory '{schemas_relative_path}' not found.")
            raise
        except yaml.YAMLError as ye:
            logging.error(f"YAML parsing error in one of the schemas: {ye}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error loading schemas: {e}")
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
                    logging.warning(f"Environment variable '{var}' not found. Using empty string as a fallback.")
                obj = obj.replace(f"${{{var}}}", env_value)
            return obj
        else:
            return obj

    def get_config(self):
        return self.config

    def get_config_value(self, key: str, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_prompt(self, prompt_name: str) -> str:
        """
        Fetch a prompt template by its name from the loaded prompts.

        :param prompt_name: Name of the prompt to retrieve.
        :return: The prompt template string.
        """
        keys = prompt_name.split('.')
        prompt = self.prompts

        # Traverse the nested dictionary using keys
        for key in keys:
            if isinstance(prompt, dict) and key in prompt:
                prompt = prompt[key]
            else:
                logging.warning(f"Prompt '{prompt_name}' not found in prompts configuration.")
                return ""

        if not isinstance(prompt, str):
            logging.warning(f"Prompt '{prompt_name}' is not a valid string in prompts configuration.")
            return ""

        return prompt

    def get_schema(self, schema_name: str) -> dict:
        """
        Fetch a schema by its name from the loaded schemas.

        :param schema_name: Name of the schema to retrieve.
        :return: The schema dictionary.
        """
        schema = self.schemas.get(schema_name)
        if not schema:
            logging.warning(f"Schema '{schema_name}' not found in schemas configuration.")
        return schema
