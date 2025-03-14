from qdrant_client.http import models as qdrant_models
from qdrant_client.models import Distance, VectorParams
from qdrant_client.http.exceptions import UnexpectedResponse
from shared_libs.utils.logger import Logger
from qdrant_client import QdrantClient
from typing import List


logger = Logger.get_logger(module_name="QdrantUtils")

def ensure_collection_exists(client:QdrantClient, collection_name: str, expected_dim: int, distance_metric: str):
    """
    Ensure that the Qdrant collection exists with the expected vector dimension.
    If the collection does not exist, create it.
    If it exists but its vector dimension does not match, log an error.
    
    :param client: An initialized Qdrant client.
    :param collection_name: Name of the collection.
    :param expected_dim: Expected vector dimension (e.g., 768).
    :param distance_metric: Distance metric as a string (e.g., "cosine").
    """
    # Convert distance metric to enum.
    distance_metric_enum = {
        "cosine": Distance.COSINE,
        "dot": Distance.DOT,
        "euclidean": Distance.EUCLID,
        "manhattan": Distance.MANHATTAN
    }.get(distance_metric.lower())
    
    if not distance_metric_enum:
        logger.error(f"Unsupported distance metric '{distance_metric}'.")
        raise ValueError(f"Unsupported distance metric '{distance_metric}'.")

    try:
        info = client.get_collection(collection_name=collection_name)
        # Use safe nested get() to retrieve the vector size.
        actual_dim = info.config.params.vectors.size
        if actual_dim != expected_dim:
            logger.error(f"Collection '{collection_name}' exists with dimension {actual_dim} but expected {expected_dim}.")
        else:
            logger.info(f"Collection '{collection_name}' exists with correct dimension {expected_dim}.")
    except Exception as e:
        # Check if the error indicates the collection doesn't exist.
        error_msg = str(e)
        if "doesn't exist" in error_msg or "Not found" in error_msg:
            logger.info(f"Collection '{collection_name}' not found. Creating new collection with dimension {expected_dim}.")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=expected_dim, distance=distance_metric_enum)
            )
            logger.info(f"Collection '{collection_name}' created successfully.")
        else:
            logger.error(f"Unexpected error while checking collection '{collection_name}': {e}")
            raise


def check_duplicate_point(client, collection_name: str, vector: List[float], threshold: float = 0.9999) -> bool:
    """
    Check whether a given vector is a duplicate of an existing point in the specified Qdrant collection.
    It performs a similarity search with top_k=1 and returns True if the similarity score is above the threshold.
    
    :param client: An initialized Qdrant client.
    :param collection_name: The Qdrant collection name.
    :param vector: The embedding vector to check.
    :param threshold: Similarity score threshold (default 0.9999) above which a point is considered a duplicate.
    :return: True if a duplicate point is found; False otherwise.
    """
    try:
        # Perform a search for the top candidate in the given collection.
        results = client.search(
            collection_name=collection_name,
            query_vector=vector,
            limit=1,
            with_payload=False
        )
        # 'results' is expected to be a list of hit objects.
        if results and len(results) > 0:
            top_hit = results[0]
            logger.debug(f"Top hit similarity score: {top_hit.score}")
            if top_hit.score >= threshold:
                logger.info(f"Duplicate detected in collection '{collection_name}' with similarity score {top_hit.score}.")
                return True
        return False
    except Exception as e:
        logger.error(f"Error during duplicate point check in collection '{collection_name}': {e}")
        return False