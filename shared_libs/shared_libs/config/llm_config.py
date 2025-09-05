# shared_libs/config/llm_config.py
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any
from .base_loader import BaseConfigLoader
from .app_config import AppConfigLoader

class LLMProviderConfig(BaseModel):
    provider: str
    model_config = {"protected_namespaces": ()}
    # Define other LLM-specific fields

class LLMConfig(BaseModel):
    llm: Dict[str, Any]

    @classmethod
    def from_app_config(cls, app_config: AppConfigLoader) -> 'LLMConfig':
        llm_section = app_config.get('llm', {})
        return cls(llm=llm_section)
    
    @classmethod
    def get(self, key: str, default=None):
        return self.llm.get(key, default)
