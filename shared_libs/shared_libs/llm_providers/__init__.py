from .openai_provider import OpenAIProvider
from .groq_provider import GroqProvider
from .gemini_provider import GeminiProvider
from .ollama_provider import OllamaProvider
from typing import Dict, Any
import os
import logging

logger = logging.getLogger(__name__)

class ProviderFactory:
    @staticmethod
    def get_provider(name: str, config: Dict[str, Any]) -> Any:
        """
        Factory method to initialize the appropriate provider based on the name.

        :param name: Name of the provider.
        :param config: Configuration dictionary for the provider.
        :return: Instance of the provider.
        """
        providers = {
            'groq': GroqProvider,
            'openai': OpenAIProvider,
            'google_gemini': GeminiProvider,
            'ollama': OllamaProvider,
            # Add other providers as needed
        }

        provider_class = providers.get(name.lower())
        if not provider_class:
            raise ValueError(f"Provider '{name}' is not supported.")

        try:
            return provider_class(config)
        except Exception as e:
            logger.error(f"Error initializing provider '{name}': {e}")
            raise

    @staticmethod
    def get_default_provider(config: Dict[str, Any]) -> Any:
        llm_config = config.get('llm', {})
        provider_name = llm_config.get('provider', 'groq')
        provider_config = llm_config.get(provider_name, {})
        try:
            return ProviderFactory.get_provider(provider_name, provider_config)
        except Exception as e:
            logger.error(f"Error initializing provider '{provider_name}': {e}")
            # Fallback to hardcoded default provider
            default_provider_name = 'groq'
            default_provider_config = {
                'api_key': os.getenv('GROQ_API_KEY', ''),
                'model_name': 'llama-3.1-8b-instant',
                'temperature': 0.7,
                'max_output_tokens': 2048,
            }
            return ProviderFactory.get_provider(default_provider_name, default_provider_config)
