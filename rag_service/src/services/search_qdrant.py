# rag_service/src/services/search_qdrant.py

from shared_libs.config.app_config import AppConfigLoader
from shared_libs.utils.logger import Logger
from typing import List, Dict, Any, Optional
import re
import os
config=AppConfigLoader()
# Configure logging
logger = Logger.get_logger(module_name=__name__)

def str_to_bool(value: str) -> bool:
    """
    Converts a string to a boolean.

    Args:
        value (str): The string to convert.

    Returns:
        bool: The converted boolean value.
    """
    return value.strip().lower() in ('true', '1', 'yes', 'y', 't')

QDRANT_LOCAL_MODE=str_to_bool(os.getenv("QDRANT_LOCAL_MODE", "False"))
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


