# shared_libs/config/base_loader.py
from pathlib import Path
import yaml
import logging
import os
import re
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseConfigLoader(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

    def load_yaml(self, file_path: Path) -> Dict[str, Any]:
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
        
