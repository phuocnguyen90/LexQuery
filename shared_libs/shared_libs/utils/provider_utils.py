# shared_libs/utils/provider_utils.py
from shared_libs.llm_providers import ProviderFactory
from shared_libs.config.config_loader import ConfigLoader

def load_llm_provider():
    """
    Loads the appropriate LLM provider based on configuration.
    Includes fallback logic to default provider.
    
    :return: Instance of the provider.
    """
    # Instantiate ConfigLoader which automatically loads the configuration
    config_loader = ConfigLoader()

    # Get the configuration dictionary
    config = config_loader.get_config()

    # Fetch requirements if they exist in the configuration
    requirements = config.get('requirements', '')

    # Use ProviderFactory to get the default provider
    return ProviderFactory.get_default_provider(config=config, requirements=requirements)
