# shared_libs/config/prompt_config.py
from pathlib import Path
from pydantic import BaseModel
from typing import Dict, Optional
from .base_loader import BaseConfigLoader

class PromptConfigLoader(BaseConfigLoader):
    PROMPTS_FILE_PATH: Path = Path(__file__).parent / 'prompts/prompts.yaml'
    prompts: Dict[str, str] = {}
    prompts_path: Path = Path(__file__).parent / 'prompts/prompts.yaml'

    def __init__(self, prompts_path: Optional[str] = None):
        super().__init__()
        self.prompts_path = Path(prompts_path) if prompts_path else self.PROMPTS_FILE_PATH
        self.prompts = self.load_yaml(self.prompts_path)

    def get_prompt(self, prompt_name: str) -> str:
        return self.prompts.get(prompt_name, "")
