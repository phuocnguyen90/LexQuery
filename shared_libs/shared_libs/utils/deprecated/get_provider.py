# shared_libs\shared_libs\llm_providers\get_provider.py
from shared_libs.utils.deprecated.config_loader import ConfigLoader
from ...llm_providers.groq_provider import GroqProvider
from ...llm_providers.openai_provider import OpenAIProvider 
from ...llm_providers.gemini_provider import GeminiProvider

# Load configuration
config = ConfigLoader().get_config()

# Get the requirements from the configuration
groq_config = config.get('llm.groq', {})
requirements = groq_config.get('processing', {}).get('pre_process_requirements', "")


# Initialize the GroqProvider
groq_provider = GroqProvider(config=groq_config, requirements=requirements)

def get_groq_provider():
    return groq_provider

def get_default_provider():
    config = ConfigLoader().get_config()
    provider_name = config.get('llm.provider', 'groq')

    if provider_name == 'openai':
        openai_config = config.get('llm.openai', {})
        return OpenAIProvider(config=openai_config, requirements=requirements)
    elif provider_name == 'groq':
        groq_config = config.get('llm.groq', {})
        return GroqProvider(config=groq_config, requirements=requirements)
    elif provider_name == 'google_gemini':
        gemini_config = config.get('llm.google_gemini', {})
        return GeminiProvider(config=gemini_config, requirements=requirements)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")