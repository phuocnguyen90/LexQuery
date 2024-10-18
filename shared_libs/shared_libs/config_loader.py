import os
import yaml
from dotenv import load_dotenv

class ConfigLoader:
    @staticmethod
    def load_config(config_path='config/config.yaml', dotenv_path='config/.env'):
        """
        Load the YAML configuration file and environment variables.

        :param config_path: Path to the YAML configuration file.
        :param dotenv_path: Path to the .env file containing environment variables.
        :return: Configuration as a Python dictionary.
        """
        # Load environment variables
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)

        # Load config YAML file
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
        else:
            config = {}

        return config
