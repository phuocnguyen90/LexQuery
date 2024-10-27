import json
import boto3
from botocore.exceptions import ClientError
from typing import List
from .base_embedder import BaseEmbedder
from embedding_service.app.config.embedding_config import EC2EmbeddingConfig
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

class EC2Embedder(BaseEmbedder):
    def __init__(self, config: EC2EmbeddingConfig):
        self.service_url = config.service_url
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name=config.region_name
        )
        self.model_id = config.model_id
        logger.info(f"Initialized EC2Embedder with model ID '{self.model_id}' in region '{config.region_name}'.")

    def embed(self, text: str) -> List[float]:
        try:
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({"text": text}),
                contentType='application/json'
            )
            response_payload = response['body'].read()
            response_json = json.loads(response_payload)
            embedding = response_json.get('embedding')
            if not embedding:
                logger.error("No embedding found in Bedrock response.")
                return []
            return embedding
        except ClientError as e:
            logger.error(f"AWS ClientError during EC2 Bedrock embed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error during EC2 Bedrock embed: {e}")
            return []

    def get_model_info(self) -> dict:
        return {
            "provider": "ec2",
            "model_id": self.model_id,
            "region_name": self.bedrock_client.meta.region_name
        }
