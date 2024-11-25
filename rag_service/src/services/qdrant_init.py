# src/services/qdrant_init.py
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, VectorParams
from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.utils.logger import Logger
from shared_libs.embeddings.embedder_factory import EmbedderFactory # Updated import
from shared_libs.config.embedding_config import EmbeddingConfig

# Load configuration from shared_libs
config = AppConfigLoader()

embedding_config=EmbeddingConfig.from_config_loader()

# Configure logging using Logger from shared_libs
logger = Logger.get_logger(module_name=__name__)

# Load Qdrant configuration
qdrant_config = config.get("qdrant", {})
QDRANT_API_KEY = qdrant_config.get("api_key")
QDRANT_URL = qdrant_config.get("url")
QA_COLLECTION_NAME = 'legal_qa'
DOC_COLLECTION_NAME = 'legal_doc'

# Set up Qdrant Client with Qdrant Cloud parameters
if not QDRANT_API_KEY or not QDRANT_URL:
    logger.error("QDRANT_API_KEY and QDRANT_URL must be set.")
    exit(1)

# Initialize the embedding function using Bedrock
embedding_function = EmbedderFactory.create_embedder('ec2')

def initialize_qdrant(local: bool = True):
    """
    Initialize a Qdrant client and configure the collection.

    :param local: Whether to use a local Qdrant server.
    :return: Initialized Qdrant client.
    """
    if local:
        logger.info("Using local Qdrant server for testing.")
        client = QdrantClient(url="http://localhost:6333") 
    else:
        if not QDRANT_API_KEY or not QDRANT_URL:
            logger.error("QDRANT_API_KEY and QDRANT_URL must be set for remote server.")
            exit(1)
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, prefer_grpc=True)
        logger.info("Using remote Qdrant server.")

    # Get vector size from embedder
    vector_size = embedding_function.vector_size()

    try:
        # Check if the collection already exists
        client.get_collection(QA_COLLECTION_NAME) 
        logger.debug(f"Collection '{QA_COLLECTION_NAME}' already exists.")
    except UnexpectedResponse:
        # If the collection does not exist, create it
        logger.debug(f"Collection '{QA_COLLECTION_NAME}' not found. Creating it now.")
        client.create_collection(
            QA_COLLECTION_NAME=QA_COLLECTION_NAME,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE  # Adjust distance metric as required
            )
        )
        logger.info(f"Collection '{QA_COLLECTION_NAME}' created successfully.")

    return client

