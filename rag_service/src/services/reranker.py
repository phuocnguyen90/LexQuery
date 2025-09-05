from typing import List, Dict, Any
from flashrank import Ranker, RerankRequest
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name="Reranker")

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
    def __init__(self, method: str = "flashrank", **kwargs):
        """
        Initialize the Reranker with a chosen method.
        
        Supported methods:
          - "flashrank": Uses the flashrank library.
          - "crossencoder": Uses a cross encoder model via HuggingFace Transformers.
          - "cohere": Uses Cohere's ranking API.
          
        Additional kwargs:
          For flashrank:
            - model (default "ms-marco-MultiBERT-L-12")
            - cache_dir (default "/opt")
            - max_length (default 128)
          For crossencoder:
            - model (default "bkai-foundation-models/vietnamese-bi-encoder")
          For cohere:
            - api (API key)
            - model (model name)
        """
        self.method = method.lower()
        self.kwargs = kwargs
        
        if self.method == "flashrank":
            if Ranker is None:
                raise ImportError("flashrank is not installed.")
            model_name = kwargs.get("model", "ms-marco-MultiBERT-L-12")
            cache_dir = kwargs.get("cache_dir", "/opt")
            max_length = kwargs.get("max_length", 128)
            self.ranker = Ranker(model_name=model_name, cache_dir=cache_dir, max_length=max_length)
            logger.info(f"Reranker initialized with flashrank using model '{model_name}'.")
        elif self.method == "crossencoder":
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            model_name = kwargs.get("model", "bkai-foundation-models/vietnamese-bi-encoder")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.max_length = kwargs.get("max_length", 256)
            logger.info(f"Reranker initialized with crossencoder using model '{model_name}'.")
        elif self.method == "phoranker":
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            model_name = kwargs.get("model", "itdainb/PhoRanker")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self.max_length = kwargs.get("max_length", 256)
            logger.info(f"Reranker initialized with PhoRanker using model '{model_name}'.")
        elif self.method == "cohere":
            # Example: using cohere's Python client
            import cohere
            api_key = kwargs.get("api", "")
            if not api_key:
                raise ValueError("API key required for cohere reranker.")
            model_name = kwargs.get("model", "default")
            self.client = cohere.Client(api_key)
            self.cohere_model = model_name
            logger.info(f"Reranker initialized with Cohere using model '{model_name}'.")
        else:
            raise ValueError(f"Unsupported reranker method: {self.method}")

    def rerank(self, query: str, passages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rerank passages based on the query using the chosen method.
        
        Args:
            query (str): The query text.
            passages (List[Dict[str, Any]]): List of passages (each should have 'id', 'text', and optionally 'meta').
            
        Returns:
            List[Dict[str, Any]]: Reranked passages with updated scores.
        """
        if self.method == "flashrank":
            return self._rerank_flashrank(query, passages)
        elif self.method == "crossencoder":
            return self._rerank_crossencoder(query, passages)
        elif self.method == "phoranker":
            return self._rerank_crossencoder(query, passages)
        elif self.method == "cohere":
            return self._rerank_cohere(query, passages)
        
        else:
            raise ValueError(f"Unsupported reranker method: {self.method}")

    def _rerank_flashrank(self, query: str, passages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            logger.debug(f"Starting flashrank reranking for query: {query}")
            rerank_request = RerankRequest(query=query, passages=passages)
            results = self.ranker.rerank(rerank_request)
            logger.debug(f"Flashrank reranking completed with {len(results)} results.")
            return results
        except Exception as e:
            logger.error(f"Flashrank reranking failed: {e}")
            return []

    def _rerank_crossencoder(self, query: str, passages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not passages:
            logger.warning("No passages provided to rerank.")
            return []

        scored_candidates = []
        for cand in passages:
            candidate_text = cand.get("text", "")
            try:
                score = self._cross_encoder_score(query, candidate_text)
            except Exception as e:
                logger.error(f"Error scoring candidate '{cand.get('id', 'unknown')}': {e}")
                score = 0  # Default or fallback score
            cand["score"] = score
            scored_candidates.append(cand)

        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates

    def _cross_encoder_score(self, query: str, candidate: str) -> float:
        import torch
        # Tokenize the combined input with truncation
        inputs = self.tokenizer(query, candidate, return_tensors="pt", truncation=True, max_length=self.max_length)
        # If the combined input fits within max_length, simply score it
        if inputs["input_ids"].shape[1] <= self.max_length:
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                # Apply sigmoid to normalize the score between 0 and 1.
                if logits.dim() == 1 or logits.size(-1) == 1:
                    score = torch.sigmoid(logits.squeeze()).item()
                else:
                    score = torch.sigmoid(logits[:, 0]).item()
            return score
        else:
            # Otherwise, split the candidate text into segments that fit
            query_tokens = self.tokenizer(query, add_special_tokens=True)["input_ids"]
            available_length = self.max_length - len(query_tokens)
            candidate_tokens = self.tokenizer(candidate, add_special_tokens=False)["input_ids"]
            segments = []
            for i in range(0, len(candidate_tokens), available_length):
                segment_tokens = candidate_tokens[i:i + available_length]
                segment_text = self.tokenizer.decode(segment_tokens, skip_special_tokens=True)
                segments.append(segment_text)
            scores = []
            for segment in segments:
                inputs_segment = self.tokenizer(query, segment, return_tensors="pt", truncation=True, max_length=self.max_length)
                with torch.no_grad():
                    outputs_segment = self.model(**inputs_segment)
                    logits_segment = outputs_segment.logits
                    if logits_segment.dim() == 1 or logits_segment.size(-1) == 1:
                        score = torch.sigmoid(logits_segment.squeeze()).item()
                    else:
                        score = torch.sigmoid(logits_segment[:, 0]).item()
                scores.append(score)
            return max(scores) if scores else 0.0


    def _rerank_cohere(self, query: str, passages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored_candidates = []
        # Example: assuming cohere's API provides a ranking function.
        # You need to refer to cohere's documentation for the exact API usage.
        for cand in passages:
            candidate_text = cand.get("text", "")
            # Here, we simulate an API call; replace with actual client code.
            response = self.client.rank(query=query, candidates=[candidate_text], model=self.cohere_model)
            # Assume the response returns a score in response["results"][0]["score"]
            score = response["results"][0]["score"] if response.get("results") else 0.0
            cand["score"] = score
            scored_candidates.append(cand)
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates

def map_qdrant_rerank(qdrant_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Map Qdrant search results to the format required by the reranker.
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
    """
    original_lookup = {result["record_id"]: result for result in original_results}
    mapped_results = []
    for reranked in reranked_results:
        record_id = reranked["id"]
        if record_id in original_lookup:
            original_result = original_lookup[record_id]
            original_result["similarity_score"] = reranked.get("score", 0)
            mapped_results.append(original_result)
        else:
            logger.warning(f"Record ID '{record_id}' not found in the original results. Skipping.")
    logger.debug(f"Original lookup: {original_lookup}")
    logger.debug(f"Reranked results: {reranked_results}")
    logger.debug(f"Final mapped results: {mapped_results}")
    return mapped_results