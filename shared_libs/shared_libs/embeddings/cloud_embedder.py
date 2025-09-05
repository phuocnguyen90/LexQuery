# shared_libs\shared_libs\embeddings\cloud_embedder.py
import requests
from typing import List, Dict, Any
from .base_embedder import BaseEmbedder
from .embedder_registry import EmbedderRegistry
from typing_extensions import Literal

# EmbedderRegistry.register("cloud", "shared_libs.embeddings.cloud_embedder", "CloudEmbedder")
class CloudEmbedder(BaseEmbedder):
    required_fields = ["service_url", "vector_dimension"]

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize CloudEmbedder with dynamic configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary for the CLOUD provider.
        """
        self.provider: Literal['cloud'] = 'cloud'

        # Validate required fields
        for field in self.required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in CLOUD configuration.")

        self.service_url = config["service_url"]
        self.vector_dimension = int(config["vector_dimension"])

    def embed(self, text: str) -> List[float]:
        response = requests.post(self.service_url, json={"texts": [text], "is_batch": False})
        response.raise_for_status()
        return response.json()["embeddings"][0]

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        response = requests.post(self.service_url, json={"texts": texts, "is_batch": True})
        response.raise_for_status()
        return response.json()["embeddings"]

    def vector_dimension(self) -> int:
        return self.vector_dimension