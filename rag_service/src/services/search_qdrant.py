# src/rag_app/search_qdrant.py

from typing import List, Dict
from qdrant_client import QdrantClient

import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Qdrant Client
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")  # Replace with your Qdrant URL
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")  # Replace with your Qdrant API Key if any
COLLECTION_NAME = "legal_qa"

qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

def search_qdrant(query: str, top_k: int = 3) -> List[Dict]:
    """
    Search Qdrant for documents similar to the query.

    :param query: The user's input query.
    :param top_k: Number of top similar documents to retrieve.
    :return: List of dictionaries containing 'record_id', 'source', and 'content'.
    """
    from get_embedding_function import get_embedding_function  

    embed_func = get_embedding_function()

    # Depending on Option 1 or 2 in get_embedding_function.py
    if hasattr(embed_func, 'embed'):
        # If using the wrapper class
        query_embedding = embed_func.embed(query)
    else:
        # If using the standalone function
        query_embedding = embed_func(query)

    if not query_embedding:
        logger.error("Failed to generate embedding for the query.")
        return []

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
