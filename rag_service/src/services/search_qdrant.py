# rag_service/src/services/search_qdrant.py

from shared_libs.config.app_config import AppConfigLoader
from shared_libs.utils.logger import Logger
from qdrant_client.http.models import Filter, FieldCondition, MatchAny, MatchText

from typing import List, Dict, Any, Optional
import re
import os
import numpy as np
config=AppConfigLoader()
# Configure logging
logger = Logger.get_logger(module_name=__name__)


DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() in ["true", "1", "yes"]

QDRANT_LOCAL_MODE= os.getenv("QDRANT_LOCAL_MODE", "False").lower() in ["true", "1", "yes"]
try:
    from .qdrant_init import initialize_qdrant
    logger.debug("Qdrant client initialized successfully.")
except: 
    from services.qdrant_init import initialize_qdrant
    logger.debug("Qdrant client initialized via direct import.")
# Initialize Qdrant client (default to local for development)
qdrant_client = initialize_qdrant()

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
    if embedding_vector is None or len(embedding_vector) == 0:
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
    
import numpy as np  # Ensure NumPy is imported if used

async def advanced_qdrant_search(
    embedding_vector: List[float],
    keywords: List[str],
    collection_name: Optional[str] = QA_COLLECTION_NAME,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """
    Perform an advanced search in Qdrant using both embedding vectors and keyword filtering.

    :param embedding_vector: The embedding vector of the query.
    :param keywords: List of keywords to filter the search results.
    :param collection_name: The name of the Qdrant collection to search.
    :param top_k: Number of top similar documents to retrieve.
    :return: List of dictionaries containing relevant document fields and similarity scores.
    """
    # Ensure embedding_vector is a list
    if isinstance(embedding_vector, np.ndarray):
        embedding_vector = embedding_vector.tolist()
    elif not isinstance(embedding_vector, list):
        logger.error("Embedding vector must be a list or NumPy array.")
        return []

    if embedding_vector is None or len(embedding_vector) == 0:
        logger.error("No embedding vector provided for Qdrant search.")
        return []

    if not isinstance(keywords, list):
        logger.error("Keywords must be a list.")
        return []

    if keywords is None or len(keywords) == 0:
        logger.error("No keywords provided for Qdrant search.")
        return []

    try:
        logger.debug(f"Performing advanced search in collection '{collection_name}' with top_k={top_k}.")

        # Construct the filter to match at least one of the keywords in the 'content' field
        keyword_conditions = [
            FieldCondition(
                key="content",
                match=MatchText(text=keyword)
            ) for keyword in keywords
        ]

        combined_filter = Filter(
            should=keyword_conditions
        )

        # Perform the search with both embedding and filter
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=embedding_vector,
            query_filter=combined_filter,  # Corrected parameter name
            limit=top_k,
            with_payload=True
        )

        # Ensure unique results based on record_id
        unique_results = {}
        for hit in search_result:
            record_id = hit.payload.get("record_id", "")
            if record_id and record_id not in unique_results:
                unique_results[record_id] = hit
        search_result = list(unique_results.values())

        # Extract relevant data from the search results
        results = []
        for hit in search_result:
            payload = hit.payload
            similarity_score = hit.score  # Access similarity score
            results.append({
                "record_id": payload.get("record_id", ""),
                "document_id": payload.get("document_id", ""),
                "title": payload.get("title", ""),
                "content": payload.get("content", ""),
                "chunk_id": payload.get("chunk_id", ""),
                "source": payload.get("source", ""),
                "model_info": payload.get("model_info", {}),
                "similarity_score": similarity_score
            })
            # Log details for debugging
            logger.debug(f"Document ID: {payload.get('record_id', '')}, "
                         f"Title: {payload.get('title', 'N/A')}, "
                         f"Similarity Score: {similarity_score:.4f}")

        if results:
            logger.debug(f"Found {len(results)} documents matching the criteria.")
        else:
            logger.warning("No documents found matching the embedding and keyword filters.")

        return results

    except Exception as e:
        logger.error(f"Error during advanced Qdrant search: {e}")
        return []

    
def reconstruct_source(source_id: str) -> str:
    """
    Reconstruct a readable source string from a source_id.

    Rules:
    - Ignore 'ch' (chapter) if present.
    - 'art' is followed by a number without hyphen (e.g., 'art002' -> 'Điều 2').
    - 'cl_' is followed by a number (e.g., 'cl_12' -> 'khoản 12').
    - 'pt_' is followed by a label (e.g., 'pt_a' -> 'điểm a').

    :param source_id: The source ID to reconstruct.
    :return: A human-readable string describing the source.
    """
    try:
        # Initialize variables
        article = None
        clause = None
        point = None

        # Patterns to match 'art', 'cl_', and 'pt_'
        art_pattern = re.compile(r'art(\d+)', re.IGNORECASE)
        cl_pattern = re.compile(r'cl_(\d+)', re.IGNORECASE)
        pt_pattern = re.compile(r'pt_(\w+)', re.IGNORECASE)

        # Search for patterns
        art_match = art_pattern.search(source_id)
        cl_match = cl_pattern.search(source_id)
        pt_match = pt_pattern.search(source_id)

        # Extract base document (everything before the first '_')
        base_document = source_id.split('_')[0]

        # Extract article number
        if art_match:
            article_number = int(art_match.group(1))
            article = f"Điều {article_number}"

        # Extract clause number
        if cl_match:
            clause_number = int(cl_match.group(1))
            clause = f"khoản {clause_number}"

        # Extract point label
        if pt_match:
            point_label = pt_match.group(1)
            point = f"điểm {point_label}"

        # Assemble the reconstructed source
        reconstructed_parts = []
        if clause:
            reconstructed_parts.append(clause)
        if article:
            reconstructed_parts.append(article)
        if point:
            reconstructed_parts.append(point)

        # Combine parts with base document
        if reconstructed_parts:
            reconstructed_source = f"{', '.join(reconstructed_parts)} văn bản {base_document}"
        else:
            # If no article, clause, or point found, just return the base document
            reconstructed_source = f"văn bản {base_document}"

        return reconstructed_source

    except Exception as e:
        logger.error(f"Failed to reconstruct source from source_id '{source_id}': {e}")
        return "Unknown Source"


