import os
import redis
import json
import boto3
import time
from botocore.exceptions import ClientError
from typing import Optional

# Environment Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"

# DynamoDB Table Configuration
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "YourCacheTableName")

# Initialize Redis connection if in development mode
cache_client = None
if DEVELOPMENT_MODE:
    cache_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Initialize DynamoDB connection
dynamodb = boto3.resource("dynamodb")
cache_table = dynamodb.Table(DYNAMODB_TABLE_NAME)

class Cache:
    @staticmethod
    def set(key: str, value: dict, expiry: int = 3600):
        """Set a value in Redis or DynamoDB with an optional expiry time."""
        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            cache_client.set(key, json.dumps(value), ex=expiry)
        else:
            # Use DynamoDB in production
            item = {
                'cache_key': key,
                'cache_value': json.dumps(value),
                'ttl': int(time.time()) + expiry  # Use TTL to auto-expire items in DynamoDB
            }
            try:
                cache_table.put_item(Item=item)
            except ClientError as e:
                print(f"Error setting item in DynamoDB cache: {e}")

    @staticmethod
    def get(key: str) -> Optional[dict]:
        """Get a value from Redis or DynamoDB."""
        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            value = cache_client.get(key)
            if value:
                return json.loads(value)
            return None
        else:
            # Use DynamoDB in production
            try:
                response = cache_table.get_item(Key={'cache_key': key})
                if 'Item' in response:
                    return json.loads(response['Item']['cache_value'])
            except ClientError as e:
                print(f"Error getting item from DynamoDB cache: {e}")
            return None

    @staticmethod
    def delete(key: str):
        """Delete a value from Redis or DynamoDB."""
        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            cache_client.delete(key)
        else:
            # Use DynamoDB in production
            try:
                cache_table.delete_item(Key={'cache_key': key})
            except ClientError as e:
                print(f"Error deleting item from DynamoDB cache: {e}")

