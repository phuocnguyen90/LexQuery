from pathlib import Path
import yaml
import logging
import os
import re
from dotenv import load_dotenv

class ConfigLoader:
    _instance = None
    _config = None

    def __new__(cls, config_path=None, dotenv_path=None):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            # Use environment variable paths if available
            config_path = config_path or os.environ.get('CONFIG_PATH', 'config/config.yaml')
            dotenv_path = dotenv_path or os.environ.get('DOTENV_PATH', 'config/.env')
            cls._instance._load_config(config_path, dotenv_path)
        return cls._instance

    @classmethod
    def _load_config(cls, config_relative_path, dotenv_relative_path):
        try:
            # Resolve the absolute path dynamically using pathlib
            base_dir = Path(__file__).resolve().parent.parent  # Get the shared_libs directory
            config_path = base_dir / config_relative_path
            dotenv_path = base_dir / dotenv_relative_path

            # Load environment variables if .env exists
            if dotenv_path.exists():
                load_dotenv(dotenv_path)
                logging.info(f"Loaded environment variables from '{dotenv_path}'.")

            # Load YAML configuration file
            with config_path.open('r', encoding='utf-8') as file:
                config = yaml.safe_load(file)

            # Substitute environment variables in the configuration
            cls._config = cls._substitute_env_vars(config)
            logging.info(f"Configuration loaded successfully from '{config_path}'.")

        except FileNotFoundError:
            logging.error(f"Configuration file '{config_path}' not found.")
            raise
        except yaml.YAMLError as ye:
            logging.error(f"YAML parsing error in '{config_path}': {ye}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error loading configuration: {e}")
            raise

    @classmethod
    def _substitute_env_vars(cls, obj):
        # Substitute environment variables
        if isinstance(obj, dict):
            return {k: cls._substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls._substitute_env_vars(element) for element in obj]
        elif isinstance(obj, str):
            pattern = re.compile(r'\$\{([^}]+)\}')
            matches = pattern.findall(obj)
            for var in matches:
                env_value = os.environ.get(var, "")
                obj = obj.replace(f"${{{var}}}", env_value)
            return obj
        else:
            return obj

    @classmethod
    def get_config(cls):
        if cls._config is None:
            raise ValueError("Configuration not loaded. Please ensure ConfigLoader is instantiated.")
        return cls._config

    @classmethod
    def get_config_value(cls, key: str, default=None):
        """
        Retrieve a specific configuration value.

        :param key: Key to retrieve.
        :param default: Default value to return if the key doesn't exist.
        :return: The configuration value or default.
        """
        return cls._config.get(key, default)

    @classmethod
    def get_prompt(cls, prompt_name: str) -> str:
        """
        Fetch a prompt template by its name from the loaded config.

        :param prompt_name: Name of the prompt to retrieve.
        :return: The prompt template string.
        """
        prompts = cls._config.get('prompts', {})
        prompt = prompts.get(prompt_name)
        if not prompt:
            logging.warning(f"Prompt '{prompt_name}' not found in configuration.")
            return ""
        return prompt

    @classmethod
    def get_schema(cls, schema_name: str) -> dict:
        """
        Fetch a schema by its name from the loaded config.

        :param schema_name: Name of the schema to retrieve.
        :return: The schema dictionary.
        """
        schemas = cls._config.get('schemas', {})
        schema = schemas.get(schema_name)
        if not schema:
            logging.warning(f"Schema '{schema_name}' not found in configuration.")
        return schema
