import requests
from typing import List, Dict
from .base_embedder import BaseEmbedder
from shared_libs.config.embedding_config import EC2EmbeddingConfig

class EC2Embedder(BaseEmbedder):
    def __init__(self, config: EC2EmbeddingConfig):
        self.service_url = config.service_url
        self.vector_dimension = config.vector_dimension

    def embed(self, text: str) -> List[float]:
        response = requests.post(self.service_url, json={"texts": [text], "is_batch": False})
        response.raise_for_status()
        return response.json()["embeddings"][0]

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        response = requests.post(self.service_url, json={"texts": texts, "is_batch": True})
        response.raise_for_status()
        return response.json()["embeddings"]
    
    def vector_size(self) -> int:
        """
        Return the vector size from the configuration.
        """
        return self.vector_dimension