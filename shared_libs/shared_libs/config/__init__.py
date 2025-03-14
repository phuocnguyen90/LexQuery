# shared_libs/config/__init__.py

from .app_config import AppConfigLoader
from .embedding_config import EmbeddingConfig
from .llm_config import LLMConfig
from .prompt_config import PromptConfigLoader
from .qdrant_config import QdrantConfig  
from typing import Optional

class Config:
    def __init__(self, config_path: Optional[str] = None, dotenv_path: Optional[str] = None):
        self.app = AppConfigLoader(config_path=config_path)
        self.embedding = EmbeddingConfig.from_config_loader(self.app)
        self.llm = LLMConfig.from_app_config(self.app)
        self.prompts = PromptConfigLoader()
        self.qdrant = QdrantConfig.from_config_loader(self.app) 

    @staticmethod
    def load(config_path: Optional[str] = None, dotenv_path: Optional[str] = None) -> 'Config':
        return Config(config_path=config_path, dotenv_path=dotenv_path)
