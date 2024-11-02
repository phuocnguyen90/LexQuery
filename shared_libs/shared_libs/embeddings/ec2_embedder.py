import requests
from typing import List, Dict
from .base_embedder import BaseEmbedder

class EC2Embedder(BaseEmbedder):
    def __init__(self, service_url: str):
        self.service_url = service_url

    def embed(self, text: str) -> List[float]:
        response = requests.post(self.service_url, json={"texts": [text], "is_batch": False})
        response.raise_for_status()
        return response.json()["embeddings"][0]

    def batch_embed(self, texts: List[str]) -> List[List[float]]:
        response = requests.post(self.service_url, json={"texts": texts, "is_batch": True})
        response.raise_for_status()
        return response.json()["embeddings"]