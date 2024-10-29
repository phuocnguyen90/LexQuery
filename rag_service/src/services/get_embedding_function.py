from models.embeddings.embedder_factory import EmbedderFactory
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
from typing import Callable

logger = Logger.get_logger(module_name=__name__)

def get_embedding_function() -> Callable[[str], list]:
    """
    Returns an instance of the appropriate embedder based on configuration.

    :return: An instance with an 'embed' method.
    """
    config_loader = ConfigLoader()
    try:
        embedder = EmbedderFactory.create_embedder(config_loader)
        model_info = embedder.get_model_info()
        logger.info(f"Using embedding provider: {model_info['provider']}")
        return embedder.embed
    except Exception as e:
        logger.error(f"Failed to initialize embedder: {e}")
        raise
