# rag_service\src\models\embeddings\docker_embedder.py

import httpx
from typing import List
from .base_embedder import BaseEmbedder
from embedding_service.app.config.embedding_config import DockerEmbeddingConfig
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

class DockerEmbedder(BaseEmbedder):
    def __init__(self, config: DockerEmbeddingConfig):
        self.service_url = config.service_url
        logger.info(f"DockerEmbedder initialized with service URL: {self.service_url}")

    def embed(self, text: str) -> List[float]:
        try:
            response = httpx.post(self.service_url, json={"text": text}, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])
            if not embedding:
                logger.error("No embedding received from Docker service.")
                return []
            return embedding
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during Docker embed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during Docker embed: {e}")
            return []
