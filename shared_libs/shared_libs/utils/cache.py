# shared_libs/utils/cache.py
import os
import redis
import time
import hashlib
import boto3
import asyncio
import json
from botocore.exceptions import ClientError
from concurrent.futures import ThreadPoolExecutor
from boto3.dynamodb.conditions import Key
from functools import partial
from typing import Optional
from shared_libs.utils.logger import Logger

# Environment Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"

# DynamoDB Configuration
CACHE_TABLE_NAME = os.getenv("CACHE_TABLE_NAME", "CacheTable")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize logger
logger = Logger.get_logger(module_name=__name__)

# Initialize Redis connection if in development mode
cache_client = None
if DEVELOPMENT_MODE:
    try:
        cache_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        cache_client.ping()  # Test if Redis is up
        logger.info("Connected to Redis for cache.")
    except redis.RedisError as e:
        logger.error(f"Error connecting to Redis: {e}")
        cache_client = None

# Initialize DynamoDB client for production
dynamodb_client = None
dynamodb_resource = None
if not DEVELOPMENT_MODE:
    try:
        dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION)
        logger.info("Connected to DynamoDB for cache.")
    except ClientError as e:
        logger.error(f"Error connecting to DynamoDB: {e}")
    except Exception as e:
        logger.error(f"Unexpected error connecting to DynamoDB: {e}")

# Initialize a ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=10)

class Cache:
    @staticmethod
    def _generate_cache_key(query_text: str) -> str:
        """Generate a consistent cache key by hashing the normalized query text."""
        normalized_key = query_text.strip().lower()
        return hashlib.md5(normalized_key.encode('utf-8')).hexdigest()

    @staticmethod
    async def set(query_text: str, value: dict, expiry: int = 3600):
        """Set a value in the cache with an optional expiry time."""
        cache_key = Cache._generate_cache_key(query_text)
        value['cache_key'] = cache_key
        value['ttl'] = int(time.time()) + expiry

        # Ensure 'query_id' is present
        if 'query_id' not in value:
            logger.error("Cannot cache item without 'query_id'.")
            raise ValueError("Cannot cache item without 'query_id'.")

        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            if cache_client:
                value_str = json.dumps(value)
                loop = asyncio.get_event_loop()
                try:
                    await loop.run_in_executor(
                        executor,
                        partial(
                            cache_client.set,
                            cache_key,
                            value_str,
                            'EX',
                            expiry
                        )
                    )
                    logger.debug(f"Cached value in Redis with cache_key: {cache_key}")
                except redis.RedisError as e:
                    logger.error(f"Error setting item in Redis cache: {e}")
        else:
            # Production mode: Use DynamoDB
            if dynamodb_resource:
                table = dynamodb_resource.Table(CACHE_TABLE_NAME)
                loop = asyncio.get_event_loop()
                try:
                    # Use partial to pass keyword arguments
                    put_item_partial = partial(table.put_item, Item=value)
                    await loop.run_in_executor(
                        executor,
                        put_item_partial
                    )
                    logger.debug(f"Cached value in DynamoDB with cache_key: {cache_key}")
                except ClientError as e:
                    logger.error(f"Failed to cache item in DynamoDB: {e.response['Error']['Message']}")
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error during put_item operation: {str(e)}")
                    raise

    @staticmethod
    async def get(query_text: str) -> Optional[dict]:
        """Get a value from the cache."""
        cache_key = Cache._generate_cache_key(query_text)

        if DEVELOPMENT_MODE:
            if cache_client:
                loop = asyncio.get_event_loop()
                try:
                    result = await loop.run_in_executor(
                        executor,
                        partial(cache_client.get, cache_key)
                    )
                    if result:
                        logger.debug(f"Cache hit in Redis for cache_key: {cache_key}")
                        return json.loads(result)
                    else:
                        logger.debug(f"Cache miss in Redis for cache_key: {cache_key}")
                except redis.RedisError as e:
                    logger.error(f"Error getting item from Redis cache: {e}")
        else:
            if dynamodb_client:
                loop = asyncio.get_event_loop()
                try:
                    response = await loop.run_in_executor(
                        executor,
                        partial(
                            dynamodb_client.query,
                            TableName=CACHE_TABLE_NAME,
                            IndexName='cache_key-index',
                            KeyConditionExpression='cache_key = :ck',
                            ExpressionAttributeValues={
                                ':ck': {'S': cache_key}
                            }
                        )
                    )
                    items = response.get('Items', [])
                    if items:
                        logger.debug(f"Cache hit in DynamoDB for cache_key: {cache_key}")
                        # Convert DynamoDB item to a regular dict
                        return {k: list(v.values())[0] for k, v in items[0].items()}
                    else:
                        logger.debug(f"Cache miss in DynamoDB for cache_key: {cache_key}")
                except ClientError as e:
                    logger.error(f"Failed to get item from DynamoDB cache: {e.response['Error']['Message']}")
                except Exception as e:
                    logger.error(f"Unexpected error during get operation: {str(e)}")
        return None

    @staticmethod
    async def delete(query_text: str):
        """Delete a value from the cache."""
        cache_key = Cache._generate_cache_key(query_text)

        if DEVELOPMENT_MODE:
            if cache_client:
                loop = asyncio.get_event_loop()
                try:
                    await loop.run_in_executor(
                        executor,
                        partial(cache_client.delete, cache_key)
                    )
                    logger.debug(f"Deleted cache entry in Redis for cache_key: {cache_key}")
                except redis.RedisError as e:
                    logger.error(f"Error deleting item from Redis cache: {e}")
        else:
            if dynamodb_client and dynamodb_resource:
                loop = asyncio.get_event_loop()
                try:
                    # First, query to get all query_ids associated with the cache_key
                    response = await loop.run_in_executor(
                        executor,
                        partial(
                            dynamodb_client.query,
                            TableName=CACHE_TABLE_NAME,
                            IndexName='cache_key-index',
                            KeyConditionExpression='cache_key = :ck',
                            ExpressionAttributeValues={
                                ':ck': {'S': cache_key}
                            }
                        )
                    )
                    items = response.get('Items', [])
                    if items:
                        table = dynamodb_resource.Table(CACHE_TABLE_NAME)
                        for item in items:
                            query_id = item.get('query_id', {}).get('S')
                            if query_id:
                                delete_item_partial = partial(table.delete_item, Key={'query_id': query_id})
                                await loop.run_in_executor(
                                    executor,
                                    delete_item_partial
                                )
                                logger.debug(f"Deleted cache entry in DynamoDB for query_id: {query_id}")
                    else:
                        logger.debug(f"No cache entry to delete in DynamoDB for cache_key: {cache_key}")
                except ClientError as e:
                    logger.error(f"Failed to delete item from DynamoDB cache: {e.response['Error']['Message']}")
                except Exception as e:
                    logger.error(f"Unexpected error during delete operation: {str(e)}")