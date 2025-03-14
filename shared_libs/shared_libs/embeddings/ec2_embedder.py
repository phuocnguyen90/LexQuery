# shared_libs\shared_libs\embeddings\ec2_embedder.py
import requests
from typing import List, Dict, Any
from .base_embedder import BaseEmbedder
from .embedder_registry import EmbedderRegistry
from typing_extensions import Literal

@EmbedderRegistry.register('ec2')
class EC2Embedder(BaseEmbedder):
    required_fields = ["service_url", "vector_dimension"]

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize EC2Embedder with dynamic configuration.

        Args:
            config (Dict[str, Any]): Configuration dictionary for the EC2 provider.
        """
        self.provider: Literal['ec2'] = 'ec2'

        # Validate required fields
        for field in self.required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in EC2 configuration.")

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