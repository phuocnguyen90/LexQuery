import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ProviderFactory:
    @staticmethod
    def get_provider(name: str, config: Dict[str, Any]) -> Any:
        """
        Factory method to lazily initialize the appropriate provider based on the name.

        :param name: Name of the provider.
        :param config: Configuration dictionary for the provider.
        :return: Instance of the provider.
        """
        providers = {
            'groq': 'shared_libs.llm_providers.groq_provider.GroqProvider',
            'openai': 'shared_libs.llm_providers.openai_provider.OpenAIProvider',
            'google_gemini': 'shared_libs.llm_providers.gemini_provider.GeminiProvider',
            'ollama': 'shared_libs.llm_providers.ollama_provider.OllamaProvider',
            # Add other providers as needed
        }

        provider_path = providers.get(name.lower())
        if not provider_path:
            raise ValueError(f"Provider '{name}' is not supported.")

        try:
            # Dynamically import the provider class
            module_name, class_name = provider_path.rsplit('.', 1)
            module = __import__(module_name, fromlist=[class_name])
            provider_class = getattr(module, class_name)

            # Initialize and return the provider
            return provider_class(config)
        except Exception as e:
            logger.error(f"Error initializing provider '{name}': {e}")
            raise

    @staticmethod
    def get_default_provider(config: Dict[str, Any]) -> Any:
        """
        Returns the default provider as defined in the configuration.
        """
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
