# providers/__init__.py

from llm_providers.openai_provider import OpenAIProvider
from llm_providers.groq_provider import GroqProvider
from llm_providers.gemini_provider import GeminiProvider
from llm_providers.ollama_provider import OllamaProvider
from typing import List, Dict, Any, Optional

class ProviderFactory:
    @staticmethod
    def get_provider(name: str, config: Dict[str, Any], requirements: str):
        """
        Factory method to initialize the appropriate provider based on the name.
        
        :param name: Name of the provider.
        :param config: Configuration dictionary for the provider.
        :param requirements: Processing requirements.
        :return: Instance of the provider.
        """
        providers = {
            'groq': GroqProvider,
            'openai': OpenAIProvider,
            'google_gemini': GeminiProvider,
            'ollama': OllamaProvider
        }
        
        provider_class = providers.get(name.lower())
        if not provider_class:
            raise ValueError(f"Provider '{name}' is not supported.")
        
        return provider_class(config, requirements)