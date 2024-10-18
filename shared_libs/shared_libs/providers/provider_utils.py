from shared_libs.utils.depreciated.load_config import ConfigLoader
from providers.groq_provider import GroqProvider
from providers.openai_provider import OpenAIProvider 
from providers.gemini_provider import GeminiProvider

# Load configuration
config = ConfigLoader().get_config()

# Get the requirements from the configuration
groq_config = config.get('groq', {})
requirements = groq_config.get('processing', {}).get('pre_process_requirements', "")


# Initialize the GroqProvider
groq_provider = GroqProvider(config=groq_config, requirements=requirements)

def get_groq_provider():
    return groq_provider

def get_default_provider():
    config = ConfigLoader().get_config()
    provider_name = config.get('provider', 'groq')

    if provider_name == 'openai':
        openai_config = config.get('openai', {})
        return OpenAIProvider(config=openai_config, requirements=requirements)
    elif provider_name == 'groq':
        groq_config = config.get('groq', {})
        return GroqProvider(config=groq_config, requirements=requirements)
    elif provider_name == 'google_gemini':
        gemini_config = config.get('google_gemini', {})
        return GeminiProvider(config=gemini_config, requirements=requirements)
    else:
        raise ValueError(f"Unsupported provider: {provider_name}")