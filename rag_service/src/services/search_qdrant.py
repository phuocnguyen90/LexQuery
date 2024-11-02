# rag_service/src/services/search_qdrant.py

from qdrant_client import QdrantClient
from time import sleep
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
from typing import List, Dict, Any
import asyncio

# Import the embedding function from existing services if needed
try:
    from services.get_embedding_function import get_embedding_function  # Absolute import for production
except ImportError:
    from get_embedding_function import get_embedding_function  # Relative import for testing

# Configure logging
logger = Logger.get_logger(module_name=__name__)

# Load configuration using ConfigLoader
config_loader = ConfigLoader()
qdrant_config = config_loader.get_config_value('qdrant', {})

QDRANT_URL = qdrant_config.get("url")
QDRANT_API_KEY = qdrant_config.get("api_key", "")
COLLECTION_NAME = config_loader.get_config_value("qdrant.collection_name", "legal_qa")

# Ensure environment variables are set properly
if not QDRANT_URL:
    logger.error("Environment variable QDRANT_URL is not set. Exiting.")
    raise EnvironmentError("QDRANT_URL is not set in the environment.")

# Initialize Qdrant Client with retry mechanism
try:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            qdrant_client = QdrantClient(
                url=QDRANT_URL,
                api_key=QDRANT_API_KEY,
                prefer_grpc=True,
                https=True
            )
            logger.debug(f"Successfully initialized Qdrant client at: {QDRANT_URL}")
            break
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Failed to initialize Qdrant client, retrying ({attempt + 1}/{max_retries})...")
                sleep(2)
            else:
                logger.error(f"Failed to initialize Qdrant client after {max_retries} attempts: {e}")
                raise e
except Exception as final_error:
    logger.error(f"Final failure to initialize Qdrant client: {final_error}")
    raise

async def search_qdrant(
    embedding_vector: List[float],
    top_k: int = 3
) -> List[Dict]:
    """
    Search Qdrant for documents similar to the query embedding.

    :param embedding_vector: The embedding vector of the query.
    :param top_k: Number of top similar documents to retrieve.
    :return: List of dictionaries containing 'record_id', 'source', and 'content'.
    """
    if not embedding_vector:
        logger.error("No embedding vector provided for Qdrant search.")
        return []

    # Step 2: Search in Qdrant
    try:
        logger.debug(f"Searching Qdrant for top {top_k} documents related to the embedding.")
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=embedding_vector,
            limit=top_k,
            with_payload=True
        )

        results = []
        for hit in search_result:
            payload = hit.payload
            results.append({
                "record_id": payload.get("record_id", ""),
                "source": payload.get("source", ""),
                "content": payload.get("content", ""),
                "model_info": payload.get("model_info", {})  # Include model info
            })

        if results:
            logger.debug(f"Found {len(results)} documents for the embedding.")
        else:
            logger.warning(f"No documents found for the given embedding.")

        return results
    except Exception as e:
        logger.error(f"Error during Qdrant search: {e}")
        return []

if __name__ == "__main__":
    async def main():
        # Test the search function locally
        sample_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Replace with a valid embedding vector
        results = await search_qdrant(sample_embedding, top_k=3)
        for idx, result in enumerate(results, 1):
            print(f"Result {idx}:")
            print(f"Record ID: {result['record_id']}")
            print(f"Source: {result['source']}")
            print(f"Content: {result['content']}")
            print(f"Model Info: {result.get('model_info', {})}\n")

    asyncio.run(main())
 