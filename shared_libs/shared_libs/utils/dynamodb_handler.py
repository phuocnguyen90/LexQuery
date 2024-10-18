# shared_libs/utils/dynamodb_handler.py

import os
import boto3
import uuid
from botocore.exceptions import ClientError
import logging

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Environment Settings
TABLE_NAME = os.getenv("TABLE_NAME", "your_table_name")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize DynamoDB Resource
if DEVELOPMENT_MODE:
    # Connect to local DynamoDB in development mode
    dynamodb = boto3.resource('dynamodb', endpoint_url="http://localhost:8000", region_name="us-east-1")
    logger.info("Connected to local DynamoDB")
else:
    # Connect to AWS-hosted DynamoDB in production mode
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    logger.info("Connected to AWS DynamoDB")

class DynamoDBHandler:
    def __init__(self, table_name=TABLE_NAME):
        self.table = dynamodb.Table(table_name)

    def save_query_item(self, query_text: str):
        """Save a query item to DynamoDB."""
        query = {
            "query_id": str(uuid.uuid4()),
            "query_text": query_text,
            "is_complete": False
        }
        try:
            self.table.put_item(Item=query)
            logger.info(f"Query item saved with query_id: {query['query_id']}")
            return query
        except ClientError as e:
            logger.error(f"Failed to save query item: {e.response['Error']['Message']}")
            return None

    def get_query_item(self, query_id: str):
        """Get a query item from DynamoDB by query_id."""
        try:
            response = self.table.get_item(Key={"query_id": query_id})
            if 'Item' in response:
                logger.info(f"Retrieved query item with query_id: {query_id}")
                return response.get("Item")
            else:
                logger.warning(f"No item found with query_id: {query_id}")
                return None
        except ClientError as e:
            logger.error(f"Failed to retrieve query item: {e.response['Error']['Message']}")
            return None
