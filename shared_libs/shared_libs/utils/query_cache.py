import os
import time
import logging
import boto3
import redis
from botocore.exceptions import ClientError

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Environment variables to determine the mode and configuration
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True") == "True"  # Default to True if not set
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
TABLE_NAME = os.getenv("PROCESSED_MESSAGES_TABLE", "ProcessedMessages")

if not DEVELOPMENT_MODE:
    # Initialize DynamoDB in production
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
else:
    # Initialize Redis in development
    cache_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


class ProcessedMessageCache:
    def __init__(self, table_name=TABLE_NAME):
        self.table_name = table_name
        if not DEVELOPMENT_MODE:
            self.table = dynamodb.Table(table_name)
        logger.info(f"ProcessedMessageCache initialized in {'development' if DEVELOPMENT_MODE else 'production'} mode.")

    def get_cached_response(self, query_text):
        """
        Retrieve a cached response based on the query_text.
        In development mode, use Redis; in production, use DynamoDB.
        """
        if DEVELOPMENT_MODE:
            try:
                cached_response = cache_client.get(query_text)
                if cached_response:
                    logger.info(f"Cache hit in Redis for query: {query_text}")
                    return cached_response.decode("utf-8")
                else:
                    logger.info(f"No cached response found in Redis for query: {query_text}")
            except Exception as e:
                logger.error(f"Error fetching cached response from Redis: {str(e)}")
            return None
        else:
            try:
                response = self.table.get_item(Key={"query_text": query_text})
                if "Item" in response:
                    logger.info(f"Cache hit in DynamoDB for query: {query_text}")
                    return response["Item"].get("response_text")
                logger.info(f"No cached response found in DynamoDB for query: {query_text}")
            except ClientError as e:
                logger.error(f"Error fetching cached response from DynamoDB: {e.response['Error']['Message']}")
            return None

    def cache_response(self, query_text, response_text):
        """
        Cache a response based on the query_text.
        In development mode, use Redis; in production, use DynamoDB.
        """
        if DEVELOPMENT_MODE:
            try:
                cache_client.set(query_text, response_text, ex=3600)  # Set expiry time to 1 hour
                logger.info(f"Response cached in Redis for query: {query_text}")
            except Exception as e:
                logger.error(f"Error caching response in Redis: {str(e)}")
        else:
            try:
                self.table.put_item(
                    Item={
                        "query_text": query_text,
                        "response_text": response_text,
                        "timestamp": int(time.time())
                    }
                )
                logger.info(f"Response cached in DynamoDB for query: {query_text}")
            except ClientError as e:
                logger.error(f"Error caching response in DynamoDB: {e.response['Error']['Message']}")

    def clear_cache(self):
        """
        Clear all cached responses.
        In development mode, flush Redis; in production, this will clear the DynamoDB table (use with caution).
        """
        if DEVELOPMENT_MODE:
            try:
                cache_client.flushdb()
                logger.info("Redis cache cleared successfully.")
            except Exception as e:
                logger.error(f"Error clearing Redis cache: {str(e)}")
        else:
            try:
                # In production, clearing the entire table would require deleting all items, which can be expensive.
                # Use with caution, and you might want to add more safety measures here.
                scan = self.table.scan()
                with self.table.batch_writer() as batch:
                    for each in scan['Items']:
                        batch.delete_item(Key={"query_text": each["query_text"]})
                logger.info("DynamoDB cache cleared successfully.")
            except ClientError as e:
                logger.error(f"Error clearing DynamoDB cache: {e.response['Error']['Message']}")


# Example usage
if __name__ == "__main__":
    cache = ProcessedMessageCache()

    # Test cache in both development and production modes
    test_query = "What are the legal implications of contract breaches?"
    test_response = "The legal implications of contract breaches can include compensatory damages, restitution, rescission, etc."

    # Cache the response
    cache.cache_response(test_query, test_response)

    # Retrieve the cached response
    response = cache.get_cached_response(test_query)
    if response:
        print(f"Retrieved cached response: {response}")
