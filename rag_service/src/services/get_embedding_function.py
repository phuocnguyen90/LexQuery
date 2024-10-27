# src/services/get_embedding_function.py

import os
import json
import boto3
from botocore.exceptions import ClientError
from langchain_aws import BedrockEmbeddings
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger

# Load configuration from shared_libs
config = ConfigLoader()

# Configure logging using Logger from shared_libs
logger = Logger.get_logger(module_name=__name__)

# Load Bedrock configuration
bedrock_config = config.get("bedrock_embedding", {})
BEDROCK_MODEL_ID = bedrock_config.get("model_id", "amazon.titan-embed-text-v2:0")  # Replace with your Bedrock model ID

# Initialize Bedrock client
bedrock_client = boto3.client(
    'bedrock-runtime',  # Ensure this service is available in your region
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

class BedrockEmbedder:
    """
    A class to interact with Amazon Bedrock for generating embeddings.
    """
    def __init__(self, model_id: str):
        """
        Initialize the BedrockEmbedder with the specified model ID.

        :param model_id: The ID of the Bedrock model to use for embedding.
        """
        self.model_id = BEDROCK_MODEL_ID
        self.embedder = BedrockEmbeddings(
            client = bedrock_client,
            model_id = self.model_id
            )


    def embed(self, text: str) -> list:
        """
        Generate an embedding for the given text using Amazon Bedrock.

        :param text: The input text string.
        :return: A list of floats representing the embedding.
        """
        try:
            response = bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    "text": text
                }),
                contentType='application/json'
            )
            response_payload = response['body'].read()
            response_json = json.loads(response_payload)
            embedding = response_json.get('embedding')  # Adjust based on Bedrock's response structure
            if not embedding:
                logger.error("No embedding found in Bedrock response.")
                return []
            return embedding
        except ClientError as e:
            logger.error(f"AWS ClientError during Bedrock embed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error during Bedrock embed: {e}")
            return []

def get_embedding_function():
    """
    Returns an instance of the BedrockEmbedder.

    :return: An instance with an 'embed' method.
    """
    return BedrockEmbedder(model_id=BEDROCK_MODEL_ID)
