# rag_service/src/services/search_qdrant.py

from shared_libs.config.app_config import AppConfigLoader
from shared_libs.utils.logger import Logger
from qdrant_client.http.models import Filter, FieldCondition, MatchAny, MatchText
from typing import List, Dict, Any, Optional
import re
import os
import numpy as np

logger = Logger.get_logger(module_name=__name__)

DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() in ["true", "1", "yes"]
QDRANT_LOCAL_MODE = os.getenv("QDRANT_LOCAL_MODE", "False").lower() in ["true", "1", "yes"]

try:
    from .qdrant_init import initialize_qdrant
except ImportError:
    from services.qdrant_init import initialize_qdrant

# Initialize Qdrant client (we assume this is OK to do globally)
qdrant_client = initialize_qdrant()

async def search_qdrant(
    embedding_vector: List[float],
    collection_name: Optional[str] = None,
    top_k: int = 3,
    qa_threshold: float = 0.7,
    doc_threshold: float = 0.8,
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Search Qdrant for documents similar to the query embedding and return only results 
    with similarity scores higher than the specified threshold for each category.
    
    If a configuration dictionary is not provided, it will be loaded via AppConfigLoader.
    
    :param embedding_vector: The embedding vector of the query.
    :param collection_name: The name of the Qdrant collection to search.
           If not provided, the QA collection name is loaded from the config.
    :param top_k: Number of top similar documents to retrieve.
    :param qa_threshold: Minimum similarity score threshold for QA records.
    :param doc_threshold: Minimum similarity score threshold for DOC records.
    :param config: Optional configuration dictionary. If not provided, it will be loaded.
    :return: List of dictionaries with document fields and similarity scores.
    """
    if embedding_vector is None or len(embedding_vector) == 0:
        logger.error("No embedding vector provided for Qdrant search.")
        return []

    # Load config if not provided.
    if config is None:
        from shared_libs.config import Config
        global_config = Config.load()

    # If no collection name was provided, load the QA collection name from config.
    if collection_name is None:
        collection_name = config.get('qdrant', {}).get("QA_COLLECTION_NAME", "legal_qa_768")
    
        # Also retrieve DOC_COLLECTION_NAME from config (if needed elsewhere).
        QA_COLLECTION_NAME = global_config.app.config.get('qdrant', {}).get("QA_COLLECTION_NAME", "legal_qa_768")
        DOC_COLLECTION_NAME = global_config.app.config.get('qdrant', {}).get("DOC_COLLECTION_NAME", "legal_doc_768")

    try:
        logger.debug(f"Searching Qdrant for top {top_k} documents in collection '{collection_name}'.")
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=embedding_vector,
            limit=top_k,
            with_payload=True
        )

        # Ensure unique results based on record_id.
        unique_results = {}
        for hit in search_result:
            record_id = hit.payload.get("record_id", "")
            if record_id not in unique_results:
                unique_results[record_id] = hit
        search_result = list(unique_results.values())

        # Determine the similarity threshold based on the collection name.
        collection_lower = collection_name.lower() if collection_name else ""
        if "qa" in collection_lower:
            threshold = qa_threshold
        elif "doc" in collection_lower:
            threshold = doc_threshold
        else:
            threshold = qa_threshold

        # Extract and filter search results based on the threshold.
        results = []
        for hit in search_result:
            payload = hit.payload
            similarity_score = hit.score
            if similarity_score >= threshold:
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
                logger.debug(f"Document ID: {payload.get('record_id', '')}, "
                             f"Title: {payload.get('title', 'N/A')}, "
                             f"Similarity Score: {similarity_score:.4f}")

        if results:
            logger.debug(f"Found {len(results)} documents with similarity score >= {threshold}.")
        else:
            logger.warning("No documents found with similarity score above the threshold.")

        return results
    except Exception as e:
        logger.error(f"Error during Qdrant search: {e}")
        return []

async def advanced_qdrant_search(
    embedding_vector: List[float],
    keywords: List[str],
    collection_name: Optional[str] = None,
    top_k: int = 10,
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Perform an advanced search in Qdrant using both embedding vectors and keyword filtering.
    
    :param embedding_vector: The embedding vector of the query.
    :param keywords: List of keywords to filter the search results.
    :param collection_name: The Qdrant collection name; if not provided, defaults from config.
    :param top_k: Number of top similar documents to retrieve.
    :param config: Optional configuration dictionary.
    :return: List of dictionaries containing document fields and similarity scores.
    """
    # Ensure embedding_vector is a list.
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

    if config is None:
        config = AppConfigLoader().config

    if collection_name is None:
        collection_name = config.get('qdrant', {}).get("QA_COLLECTION_NAME", "legal_qa")

    try:
        logger.debug(f"Performing advanced search in collection '{collection_name}' with top_k={top_k}.")

        # Construct a filter to match any of the keywords in the 'content' field.
        keyword_conditions = [
            FieldCondition(
                key="content",
                match=MatchText(text=keyword)
            ) for keyword in keywords
        ]

        combined_filter = Filter(should=keyword_conditions)

        # Perform the search with both embedding and the constructed filter.
        search_result = qdrant_client.search(
            collection_name=collection_name,
            query_vector=embedding_vector,
            query_filter=combined_filter,
            limit=top_k,
            with_payload=True
        )

        unique_results = {}
        for hit in search_result:
            record_id = hit.payload.get("record_id", "")
            if record_id and record_id not in unique_results:
                unique_results[record_id] = hit
        search_result = list(unique_results.values())

        results = []
        for hit in search_result:
            payload = hit.payload
            similarity_score = hit.score
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
    Reconstruct a human-readable source string from a source_id.
    
    Rules:
      - Ignores 'ch' (chapter) if present.
      - Converts 'art' numbers to "Điều <number>".
      - Converts 'cl_' to "khoản <number>".
      - Converts 'pt_' to "điểm <label>".
    
    :param source_id: The source ID to reconstruct.
    :return: A human-readable description.
    """
    try:
        article = None
        clause = None
        point = None

        art_pattern = re.compile(r'art(\d+)', re.IGNORECASE)
        cl_pattern = re.compile(r'cl_(\d+)', re.IGNORECASE)
        pt_pattern = re.compile(r'pt_(\w+)', re.IGNORECASE)

        art_match = art_pattern.search(source_id)
        cl_match = cl_pattern.search(source_id)
        pt_match = pt_pattern.search(source_id)

        base_document = source_id.split('_')[0]

        if art_match:
            article_number = int(art_match.group(1))
            article = f"Điều {article_number}"
        if cl_match:
            clause_number = int(cl_match.group(1))
            clause = f"khoản {clause_number}"
        if pt_match:
            point_label = pt_match.group(1)
            point = f"điểm {point_label}"

        reconstructed_parts = []
        if clause:
            reconstructed_parts.append(clause)
        if article:
            reconstructed_parts.append(article)
        if point:
            reconstructed_parts.append(point)

        if reconstructed_parts:
            reconstructed_source = f"{', '.join(reconstructed_parts)} văn bản {base_document}"
        else:
            reconstructed_source = f"văn bản {base_document}"

        return reconstructed_source

    except Exception as e:
        logger.error(f"Failed to reconstruct source from source_id '{source_id}': {e}")
        return "Unknown Source"
