from typing import List, Dict, Any
from flashrank import Ranker, RerankRequest
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

class Passage:
    def __init__(self, id: str, text: str, meta: Dict[str, Any] = None):
        self.id = id
        self.text = text
        self.meta = meta or {}

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def __getitem__(self, item):
        if item == "id":
            return self.id
        elif item == "text":
            return self.text
        elif item == "meta":
            return self.meta
        raise KeyError(f"Invalid key '{item}' for Passage.")

    def __setitem__(self, item, value):
        if item == "id":
            self.id = value
        elif item == "text":
            self.text = value
        elif item == "meta":
            self.meta = value
        else:
            raise KeyError(f"Invalid key '{item}' for Passage.")


class Reranker:
    def __init__(self, model_name: str = "ms-marco-MultiBERT-L-12", cache_dir: str = "/opt", max_length: int = 128):
        try:
            self.ranker = Ranker(model_name=model_name, cache_dir=cache_dir, max_length=max_length)
            logger.info(f"Reranker initialized with model '{model_name}'")
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            raise

    def rerank(self, query: str, passages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank the passages based on the query.

        Args:
            query (str): The query text.
            passages (List[Dict[str, Any]]): List of dictionaries with `id`, `text`, and optional `meta`.

        Returns:
            List[Dict[str, Any]]: Reranked list of passages with scores.
        """
        try:
            logger.debug(f"Starting reranking for query: {query}")
            logger.debug(f"Received {len(passages)} passages for reranking.")

            # Prepare the rerank request
            rerank_request = RerankRequest(query=query, passages=passages)
            logger.debug(f"RerankRequest created with query: '{query}' and {len(passages)} passages.")

            # Perform reranking
            results = self.ranker.rerank(rerank_request)
            logger.debug(f"Reranking completed. Received {len(results)} results.")

            return results
        except Exception as e:
            logger.error(f"Failed to rerank passages: {e}")
            return []
        

def map_qdrant_rerank(qdrant_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Map Qdrant search results to the format required by the Reranker.

    Args:
        qdrant_results (List[Dict[str, Any]]): Results from Qdrant search.

    Returns:
        List[Dict[str, Any]]: Mapped results as dictionaries for the Reranker.
    """
    mapped_results = []
    for result in qdrant_results:
        if "content" not in result or not result["content"]:
            logger.warning(f"Skipping result without content: {result}")
            continue

        mapped_results.append({
            "id": result.get("record_id", ""),
            "text": result.get("content", ""),
            "meta": {
                "document_id": result.get("document_id", ""),
                "title": result.get("title", ""),
                "chunk_id": result.get("chunk_id", ""),
                "source": result.get("source", ""),
                "model_info": result.get("model_info", {})
            }
        })
    return mapped_results

def map_rerank_qdrant(
    reranked_results: List[Dict[str, Any]], 
    original_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Map reranked results back to the original structure with updated order and scores.

    Args:
        reranked_results (List[Dict[str, Any]]): Results after reranking, containing 'id', 'text', 'meta', and 'score'.
        original_results (List[Dict[str, Any]]): Original results from `search_qdrant`.

    Returns:
        List[Dict[str, Any]]: Results in the original structure with updated order and scores.
    """
    # Create a lookup table for the original results by `record_id`
    original_results_lookup = {result["record_id"]: result for result in original_results}

    # Map reranked results back to the original structure
    mapped_results = []
    for reranked in reranked_results:
        record_id = reranked["id"]
        if record_id in original_results_lookup:
            original_result = original_results_lookup[record_id]
            # Update the original result with the new score
            original_result["similarity_score"] = reranked["score"]
            mapped_results.append(original_result)
        else:
            # Handle cases where `record_id` is not found in the original results
            logger.warning(f"Record ID '{record_id}' not found in the original results. Skipping.")
    logger.debug(f"Original results lookup: {original_results_lookup}")
    logger.debug(f"Reranked results: {reranked_results}")
    logger.debug(f"Final mapped results: {mapped_results}")

    return mapped_results