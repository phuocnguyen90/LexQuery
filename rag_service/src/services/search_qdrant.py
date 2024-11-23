# rag_service/src/services/search_qdrant.py

from qdrant_client import QdrantClient
from time import sleep
from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.utils.logger import Logger
from typing import List, Dict, Any

# Configure logging
logger = Logger.get_logger(module_name=__name__)

# Load configuration using ConfigLoader
config_loader = AppConfigLoader()
qdrant_config = config_loader.get('qdrant', {})

QDRANT_URL = qdrant_config.get("url")
QDRANT_API_KEY = qdrant_config.get("api_key", "")
COLLECTION_NAME = qdrant_config.get("qdrant.collection_name", "legal_qa")

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
    :return: List of dictionaries containing 'record_id', 'source', 'content', and similarity score.
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
        unique_results = {}
        for hit in search_result:
            record_id = hit.payload.get("record_id", "")
            if record_id not in unique_results:
                unique_results[record_id] = hit
        search_result = list(unique_results.values())

        results = []
        for hit in search_result:
            payload = hit.payload
            similarity_score = hit.score  # Access similarity score
            results.append({
                "record_id": payload.get("record_id", ""),
                "source": payload.get("source", ""),
                "content": payload.get("content", ""),
                "model_info": payload.get("model_info", {}),  # Include model info
                "similarity_score": similarity_score  # Include similarity score
            })
            # Log the similarity score for each result
            logger.debug(f"Document ID: {payload.get('record_id', '')}, "
                         f"Similarity Score: {similarity_score:.4f}")

        if results:
            logger.debug(f"Found {len(results)} documents for the embedding.")
        else:
            logger.warning(f"No documents found for the given embedding.")

        return results
    except Exception as e:
        logger.error(f"Error during Qdrant search: {e}")
        return []


