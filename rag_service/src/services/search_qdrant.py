# src/services/search_qdrant.py


import logging
from qdrant_client import QdrantClient
from time import sleep
from shared_libs.config.config_loader import ConfigLoader
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console Handler with UTF-8 Encoding to avoid UnicodeEncodeError
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logger.addHandler(console_handler)

# Load configuration using ConfigLoader
config_loader = ConfigLoader()
qdrant_config = config_loader.get_config_value('qdrant', {})

QDRANT_URL = qdrant_config.get("url")
QDRANT_API_KEY = qdrant_config.get("api_key", "")
COLLECTION_NAME='legal_qa'

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
            logger.info(f"Successfully initialized Qdrant client at: {QDRANT_URL}")
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

# Import the embedding function from existing services
from get_embedding_function import get_embedding_function

# Load the embedding function, which can be FastEmbedWrapper or an external provider
embed_function_wrapper = get_embedding_function()

def search_qdrant(query: str, top_k: int = 3) -> List[Dict]:
    """
    Search Qdrant for documents similar to the query.

    :param query: The user's input query.
    :param top_k: Number of top similar documents to retrieve.
    :return: List of dictionaries containing 'record_id', 'source', and 'content'.
    """
    if not embed_function_wrapper:
        logger.error("Embedding function wrapper is not properly initialized.")
        return []

    # Step 1: Generate the embedding for the query text
    try:
        # Using the `embed()` method of `FastEmbedWrapper` to generate embeddings
        if hasattr(embed_function_wrapper, 'embed'):
            query_embedding = embed_function_wrapper.embed(query)
        else:
            raise ValueError("Invalid embedding function wrapper. Must have an 'embed()' method.")
    except Exception as e:
        logger.error(f"Failed to generate embedding for the query '{query}': {e}")
        return []

    if not query_embedding:
        logger.error("No embedding returned for the query.")
        return []

    # Step 2: Search in Qdrant
    try:
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k,
            with_payload=True
        )

        results = []
        for hit in search_result:
            payload = hit.payload
            results.append({
                "record_id": payload.get("record_id", ""),
                "source": payload.get("source", ""),
                "content": payload.get("content", "")
            })

        return results
    except Exception as e:
        logger.error(f"Error during Qdrant search: {e}")
        return []

if __name__ == "__main__":
    from shared_libs.config.config_loader import ConfigLoader
    config=ConfigLoader()
    # Test the search function locally
    sample_query = "Quy trình đăng ký doanh nghiệp tại Việt Nam là gì?"
    results = search_qdrant(sample_query, top_k=3)
    for idx, result in enumerate(results, 1):
        print(f"Result {idx}:")
        print(f"Record ID: {result['record_id']}")
        print(f"Source: {result['source']}")
        print(f"Content: {result['content']}\n")
