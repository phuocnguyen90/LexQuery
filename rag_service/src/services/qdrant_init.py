from qdrant_client import QdrantClient
from shared_libs.utils.logger import Logger
from shared_libs.config import Config

logger = Logger.get_logger(module_name=__name__)

def initialize_qdrant() -> QdrantClient:
    # Load your configuration from your unified Config
    config = Config.load()
    qdrant_conf = config.qdrant
    local = qdrant_conf.local

    if local:
        logger.info("Using local Qdrant server.")
        client = QdrantClient(url="http://localhost:6333")
    else:
        client = QdrantClient(
            url=qdrant_conf.api.url,
            api_key=qdrant_conf.api.api_key,
            prefer_grpc=True
        )
        logger.info("Using remote Qdrant server.")
    return client
