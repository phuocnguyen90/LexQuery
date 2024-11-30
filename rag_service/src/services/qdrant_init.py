# src/services/qdrant_init.py

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, VectorParams
from shared_libs.config import Config
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.utils.logger import Logger
from shared_libs.embeddings.embedder_factory import EmbedderFactory

# Initialize the centralized configuration
# Load configuration
config = Config()
config_loader = AppConfigLoader()
embedding_config = EmbeddingConfig.from_config_loader(config_loader)
# Initialize EmbedderFactory
factory = EmbedderFactory(embedding_config)

# Initialize logging using Logger from shared_libs
logger = Logger.get_logger(module_name=__name__)

# Initialize the embedding function using the configured embedder

embedding_function = factory.create_embedder('ec2')  

def initialize_qdrant():
    """
    Initialize a Qdrant client and configure the collections.
    """
    config = Config()
    qdrant_config = config.qdrant.api
    qa_collection_name = config.qdrant.collection_names.get("qa_collection", "legal_qa")
    doc_collection_name = config.qdrant.collection_names.get("doc_collection", "legal_doc")
    distance_metric = config.qdrant.distance_metric
    local = config.qdrant.local

    # Set up Qdrant Client with Qdrant Cloud parameters
    if not qdrant_config.api_key or not qdrant_config.url:
        if not local:
            logger.error("QDRANT_API_KEY and QDRANT_URL must be set for remote server.")
            exit(1)
        else:
            logger.warning("QDRANT_API_KEY and QDRANT_URL not set. Falling back to local Qdrant server.")

    # Initialize the Qdrant client
    if local:
        logger.info("Using local Qdrant server for testing.")
        client = QdrantClient(url="http://localhost:6333")
    else:
        client = QdrantClient(
            url=qdrant_config.url,
            api_key=qdrant_config.api_key,
            prefer_grpc=True
        )
        logger.info("Using remote Qdrant server.")

    # Get vector size from embedder
    if hasattr(embedding_function, 'vector_size'):
        vector_size = embedding_function.vector_size()
    elif hasattr(embedding_function, 'vector_dimension'):
        vector_size = embedding_function.vector_dimension
    else:
        logger.error("Embedding function does not have a 'vector_size' or 'vector_dimension' attribute.")
        exit(1)

    # Validate distance metric
    distance_metric_enum = {
        "cosine": Distance.COSINE,
        "dot": Distance.DOT
    }.get(distance_metric.lower())

    if not distance_metric_enum:
        logger.error(f"Unsupported distance metric '{distance_metric}'.")
        exit(1)

    def ensure_collection_exists(collection_name: str):
        """
        Ensure a Qdrant collection exists; create it if it doesn't.
        """
        try:
            client.get_collection(collection_name)
            logger.debug(f"Collection '{collection_name}' already exists.")
        except UnexpectedResponse:
            logger.debug(f"Collection '{collection_name}' not found. Creating it now.")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance_metric_enum
                )
            )
            logger.info(f"Collection '{collection_name}' created successfully.")
        except Exception as e:
            # Handle gRPC error for a missing collection
            if "Collection" in str(e) and "doesn't exist" in str(e):
                logger.debug(f"Collection '{collection_name}' not found. Creating it now.")
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=distance_metric_enum
                    )
                )
                logger.info(f"Collection '{collection_name}' created successfully.")
            else:
                logger.error(f"Unexpected error while checking collection '{collection_name}': {e}")
                raise


    # Ensure QA and Document collections exist
    ensure_collection_exists(qa_collection_name)
    ensure_collection_exists(doc_collection_name)

    return client


# Example Usage
if __name__ == "__main__":
    qdrant_client = initialize_qdrant()
    logger.info("Qdrant client initialized successfully.")
