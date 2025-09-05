from typing import List, Dict, Any, Literal
from .base_embedder import BaseEmbedder
from .embedder_registry import EmbedderRegistry
from shared_libs.utils.logger import Logger

import os
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

logger = Logger.get_logger(module_name=__name__)

# Register as a new provider. You can reference this by provider name: "local_gemma3"
EmbedderRegistry.register(    "local_gemma3",    "shared_libs.embeddings.gemma_embedder",   "GemmaLocalEmbedder",)


class GemmaLocalEmbedder(BaseEmbedder):
    """
    Local embedder using Google's EmbeddingGemma (Gemma 3) via Sentence Transformers.

    This is a drop-in provider compatible with the BaseEmbedder API, intended as a
    replacement for e5-large-based local embeddings. It supports task-optimized
    query/document encoders and Matryoshka truncation (768/512/256/128).

    Required config keys (matches your factory expectations):
      - model_name:        Hugging Face model id, e.g. "google/embeddinggemma-300m"
      - cache_dir:         Local cache dir for model weights
      - vector_dimension:  Expected output dimension (should equal truncate_dim)

    Optional config keys:
      - truncate_dim:      One of {768, 512, 256, 128}. Defaults to vector_dimension
      - similarity:        "cosine" (default) or "dot"; influences internal normalization
      - normalize:         bool (default True). If True, outputs are L2-normalized
      - inference_mode:    "auto" (default), "document", or "query"
      - query_length_threshold: int, used in auto mode (default 256 chars)
      - device:            "cuda" or "cpu" (default: auto-detect)
    """

    required_fields = ["model_name", "cache_dir", "vector_dimension"]

    def __init__(self, config: Dict[str, Any]):
        self.provider: Literal["local_gemma3"] = "local_gemma3"

        # Validate required fields
        for field in self.required_fields:
            if field not in config:
                raise ValueError(
                    f"Missing required field '{field}' in local_gemma3 configuration."
                )

        self.model_name: str = str(config["model_name"])  # e.g., "google/embeddinggemma-300m"
        self.cache_dir: str = str(config["cache_dir"])    # cache folder path

        # The factory’s EmbeddingConfig carries an expected vector size; we validate against the model
        requested_dim = int(config["vector_dimension"])   # required by your current config schema

        # Optional settings
        self.truncate_dim: int = int(config.get("truncate_dim", requested_dim))
        self.similarity: str = str(config.get("similarity", "cosine")).lower()
        self.normalize: bool = bool(config.get("normalize", True))
        self.inference_mode: str = str(config.get("inference_mode", "auto")).lower()
        self.query_length_threshold: int = int(config.get("query_length_threshold", 256))
        self.device: str = str(
            config.get("device") or ("cuda" if torch.cuda.is_available() else "cpu")
        )

        # Build SentenceTransformer model
        try:
            # similarity_fn_name controls score calculation in SentenceTransformers utilities
            st_kwargs: Dict[str, Any] = {
                "cache_folder": self.cache_dir,
            }
            # Only pass truncate_dim if it's valid for Matryoshka
            if self.truncate_dim in (768, 512, 256, 128):
                st_kwargs["truncate_dim"] = self.truncate_dim
            if self.similarity in ("cosine", "dot"):
                st_kwargs["similarity_fn_name"] = self.similarity

            self._model = SentenceTransformer(self.model_name, **st_kwargs).to(self.device)

            # Determine actual embedding size from the instantiated model
            self._vector_dimension: int = int(
                self._model.get_sentence_embedding_dimension()
            )

            if requested_dim != self._vector_dimension:
                logger.warning(
                    "Configured vector_dimension=%s does not match model output dim=%s; "
                    "continuing with %s. Update your EmbeddingConfig to avoid mismatches.",
                    requested_dim,
                    self._vector_dimension,
                    self._vector_dimension,
                )
        except Exception as e:
            logger.error(
                "Failed to initialize EmbeddingGemma model '%s': %s", self.model_name, e
            )
            raise

        logger.info(
            "Initialized EmbeddingGemma model '%s' (dim=%d, device=%s, truncate_dim=%s, similarity=%s)",
            self.model_name,
            self._vector_dimension,
            self.device,
            self.truncate_dim,
            self.similarity,
        )

    # ---- BaseEmbedder API -------------------------------------------------
    def embed(self, text: str) -> List[float]:
        try:
            return self.batch_embed([text])[0]
        except Exception as e:
            logger.error("Failed to embed text. Error: %s", e)
            raise

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            vecs = self._encode(texts)
            # Convert to Python lists for downstream compatibility
            return [v.astype(np.float32).tolist() for v in vecs]
        except Exception as e:
            logger.error("Failed to embed batch of %d texts. Error: %s", len(texts), e)
            raise

    def vector_dimension(self) -> int:  # NOTE: method name distinct from attribute
        return self._vector_dimension

    # ---- Internal helpers -------------------------------------------------
    def _encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts using task-optimized heads. In 'auto' mode, short strings
        are treated as queries, longer ones as documents.
        """
        mode = self.inference_mode
        with torch.inference_mode():
            if mode == "query":
                return self._model.encode_query(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=self.normalize,
                )
            if mode == "document":
                return self._model.encode_document(
                    texts,
                    convert_to_numpy=True,
                    normalize_embeddings=self.normalize,
                )

            # auto mode: simple heuristic on length
            is_query = [len(t) < self.query_length_threshold for t in texts]
            q_texts = [t for t, q in zip(texts, is_query) if q]
            d_texts = [t for t, q in zip(texts, is_query) if not q]

            q_vecs = (
                self._model.encode_query(
                    q_texts, convert_to_numpy=True, normalize_embeddings=self.normalize
                )
                if q_texts
                else np.zeros((0, self._vector_dimension), dtype=np.float32)
            )
            d_vecs = (
                self._model.encode_document(
                    d_texts, convert_to_numpy=True, normalize_embeddings=self.normalize
                )
                if d_texts
                else np.zeros((0, self._vector_dimension), dtype=np.float32)
            )

            # Reassemble in original order
            out: List[np.ndarray] = []
            qi = di = 0
            for q in is_query:
                if q:
                    out.append(q_vecs[qi])
                    qi += 1
                else:
                    out.append(d_vecs[di])
                    di += 1
            return np.vstack(out)
