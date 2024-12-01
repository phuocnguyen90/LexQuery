# shared_libs\shared_libs\utils\llm_init.py
from shared_libs.utils.deprecated.config_loader import AppConfigLoader, LLMProviderConfigLoader
from shared_libs.llm_providers import ProviderFactory

def initialize_llm_provider():
    try:
        # Load the application configuration
        app_config_loader = AppConfigLoader()
        config = app_config_loader.config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        config = {}

    # Initialize the LLMProviderConfigLoader
    llm_provider_loader = LLMProviderConfigLoader(config)

    # Get the default provider name and configuration
    provider_name = llm_provider_loader.get_default_provider_name()
    try:
        provider_config = llm_provider_loader.get_default_provider_config()
    except ValueError as e:
        print(f"Error obtaining default provider configuration: {e}")
        # Provide hardcoded default configuration
        provider_name = 'groq'
        provider_config = llm_provider_loader._get_hardcoded_default_config(provider_name)

    # Initialize the LLM provider
    try:
        llm_provider = ProviderFactory.get_provider(provider_name, provider_config)
    except Exception as e:
        print(f"Error initializing provider '{provider_name}': {e}")
        # As a last resort, initialize a hardcoded default provider
        provider_name = 'groq'
        provider_config = llm_provider_loader._get_hardcoded_default_config(provider_name)
        llm_provider = ProviderFactory.get_provider(provider_name, provider_config)

    return llm_provider

