# shared_libs/config/app_config.py
from pydantic import Field
from pathlib import Path
from .base_loader import BaseConfigLoader
from typing import Optional
from dotenv import load_dotenv
from logging import Logger
logger = Logger(__name__)

class AppConfigLoader(BaseConfigLoader):
    CONFIG_DIR: Path = Path(__file__).parent.resolve()
    CONFIG_FILE_PATH: Path = CONFIG_DIR / 'config.yaml'
    config_path: Optional[Path] = Field(None, description="Path to the configuration file.")
    dotenv_path: Optional[str] = Field(None, description="Path to the .env file.")
    config: dict = {}

    def __init__(self, config_path: Optional[str] = None, dotenv_path: Optional[str] = None):
        super().__init__()
        self.config_path = Path(config_path) if config_path else self.CONFIG_FILE_PATH
        self.load_configuration(dotenv_path)

    def load_configuration(self, dotenv_path: Optional[str]):
        # Load environment variables
        self._load_environment_variables(Path(dotenv_path) if dotenv_path else None)

        # Load YAML configuration
        self.config = self.load_yaml(self.config_path)


    def get(self, key: str, default=None):
        return self.config.get(key, default)
        
    def _load_environment_variables(self, dotenv_path: Optional[Path] = None):
        try:
            # Default to a `.env` file in the CONFIG_DIR if no path is provided
            dotenv_file = Path(dotenv_path) if dotenv_path else self.CONFIG_DIR / ".env"

            if dotenv_file.exists():
                load_dotenv(dotenv_file)
                logger.debug(f"Loaded environment variables from '{dotenv_file}'.")
            else:
                logger.warning(f".env file not found at '{dotenv_file}'")
        except Exception as e:
            logger.error(f"Unexpected error loading environment variables: {e}")
            raise




