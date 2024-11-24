# rag_service/src/services/search_qdrant.py

from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.utils.logger import Logger
from typing import List, Dict, Any, Optional

config=AppConfigLoader()
# Configure logging
logger = Logger.get_logger(module_name=__name__)

try:
    from qdrant_init import initialize_qdrant
    logger.debug("Qdrant client initialized successfully.")
except: 
    from services.qdrant_init import initialize_qdrant
    logger.debug("Qdrant client initialized via direct import.")
# Initialize Qdrant client (default to local for development)
qdrant_client = initialize_qdrant(local=True)

# default collection to search: QA collection
QA_COLLECTION_NAME = config.get('qdrant').get("QA_COLLECTION_NAME", "legal_qa")

async def search_qdrant(
    embedding_vector: List[float],
    collection_name: Optional[str] = QA_COLLECTION_NAME,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Search Qdrant for documents similar to the query embedding.

    :param embedding_vector: The embedding vector of the query.
    :param collection_name: The name of the Qdrant collection to search.
    :param top_k: Number of top similar documents to retrieve.
    :return: List of dictionaries containing all relevant document fields and similarity score.
    """
    if not embedding_vector:
        logger.error("No embedding vector provided for Qdrant search.")
        return []

    try:
        logger.debug(f"Searching Qdrant for top {top_k} documents in collection '{collection_name}'.")
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=embedding_vector,
            limit=top_k,
            with_payload=True
        )

        # Ensure unique results based on record_id
        unique_results = {}
        for hit in search_result:
            record_id = hit.payload.get("record_id", "")
            if record_id not in unique_results:
                unique_results[record_id] = hit
        search_result = list(unique_results.values())

        # Extract relevant data from the search results
        results = []
        for hit in search_result:
            payload = hit.payload
            similarity_score = hit.score  # Access similarity score
            results.append({
                "record_id": payload.get("record_id", ""),
                "document_id": payload.get("document_id", ""),  # Added document_id
                "title": payload.get("title", ""),  # Added title
                "content": payload.get("content", ""),
                "chunk_id": payload.get("chunk_id", ""),  # Added chunk_id
                "source": payload.get("source", ""),
                "model_info": payload.get("model_info", {}),  # Include model info
                "similarity_score": similarity_score  # Include similarity score
            })
            # Log details for debugging
            logger.debug(f"Document ID: {payload.get('record_id', '')}, "
                         f"Title: {payload.get('title', 'N/A')}, "
                         f"Similarity Score: {similarity_score:.4f}")

        if results:
            logger.debug(f"Found {len(results)} documents for the embedding.")
        else:
            logger.warning(f"No documents found for the given embedding.")

        return results
    except Exception as e:
        logger.error(f"Error during Qdrant search: {e}")
        return []