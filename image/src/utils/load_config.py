# src/utils/load_config.py
from pathlib import Path
import yaml
import logging
import os
import re

class ConfigLoader:
    _instance = None

    def __new__(cls, config_path=None, dotenv_path=None):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            # Use environment variable paths if available
            config_path = config_path or os.environ.get('CONFIG_PATH', 'config/config.yaml')
            dotenv_path = dotenv_path or os.environ.get('DOTENV_PATH', 'config/.env')
            cls._instance.load_config(config_path, dotenv_path)
        return cls._instance


    def load_config(self, config_relative_path, dotenv_relative_path):
        try:
            # Resolve the absolute path dynamically using pathlib
            base_dir = Path(__file__).resolve().parent.parent  # Get the /image/src directory
            config_path = base_dir / config_relative_path
            dotenv_path = base_dir / dotenv_relative_path

            # Load environment variables if .env exists
            if dotenv_path.exists():
                from dotenv import load_dotenv
                load_dotenv(dotenv_path)
                logging.info(f"Loaded environment variables from '{dotenv_path}'.")

            # Load YAML configuration file
            with config_path.open('r', encoding='utf-8') as file:
                config = yaml.safe_load(file)

            # Substitute environment variables in the configuration
            config = self.substitute_env_vars(config)
            self.config = config
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

    def substitute_env_vars(self, obj):
        # Substitute environment variables
        if isinstance(obj, dict):
            return {k: self.substitute_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self.substitute_env_vars(element) for element in obj]
        elif isinstance(obj, str):
            pattern = re.compile(r'\$\{([^}]+)\}')
            matches = pattern.findall(obj)
            for var in matches:
                env_value = os.environ.get(var, "")
                obj = obj.replace(f"${{{var}}}", env_value)
            return obj
        else:
            return obj

    def get_config(self):
        return self.config
