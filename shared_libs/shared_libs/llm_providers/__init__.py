from .openai_provider import OpenAIProvider
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
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

    @staticmethod
    def get_default_provider(config: Dict[str, Any], requirements: str) -> Any:
        """
        Get the default provider, with fallback to a secondary provider if needed.
        """
        try:
            # Attempt to get primary provider
            primary_provider_name = config.get("provider", "groq")
            return ProviderFactory.get_provider(primary_provider_name, config.get(primary_provider_name, {}), requirements)
        except ValueError as e:
            # Fallback to Groq if primary is not configured properly
            fallback_provider_name = "groq"
            return ProviderFactory.get_provider(fallback_provider_name, config.get(fallback_provider_name, {}), requirements)
