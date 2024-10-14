# src/utils/load_config.py
import yaml
import logging
import re
from dotenv import load_dotenv

import os
# logging.getLogger(__name__)


class ConfigLoader:
    _instance = None

    def __new__(cls, config_path='src/config/config.yaml', dotenv_path='src/config/.env'):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance.load_config(config_path, dotenv_path)
        return cls._instance

    def load_config(self, config_path, dotenv_path):
        try:
            # Load environment variables
            if os.path.exists(dotenv_path):
                from dotenv import load_dotenv
                load_dotenv(dotenv_path)
                logging.info(f"Loaded environment variables from '{dotenv_path}'.")

            # Load YAML configuration file
            with open(config_path, 'r', encoding='utf-8') as file:
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