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
        logger.error(f"Error connecting to DynamoDB: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Unexpected error connecting to DynamoDB: {e}")

# Initialize a ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=2)

class Cache:
    @staticmethod
    def _generate_cache_key(query_text: str) -> str:
        """Generate a consistent cache key by hashing the normalized query text."""
        normalized_key = query_text.strip().lower()
        return hashlib.md5(normalized_key.encode('utf-8')).hexdigest()

    @staticmethod
    async def set(query_text: str, value: dict, expiry: int = 3600):
        """
        Set a value in the cache with an optional expiry time.
        
        Args:
            query_text (str): The original query text.
            value (dict): The data to cache. Must include 'query_id'.
            expiry (int): Time to live for the cache entry in seconds.
        """
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
                            ex=expiry  # Redis expects 'ex' for expiry in seconds
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
                    # Convert the value dict to DynamoDB item format
                    dynamodb_item = Cache._convert_to_dynamodb_item(value)
                    
                    # Use conditional expression to handle TTL if necessary
                    await loop.run_in_executor(
                        executor,
                        partial(
                            table.put_item,
                            Item=dynamodb_item,
                            ConditionExpression='attribute_not_exists(query_id) OR ttl < :current_time',
                            ExpressionAttributeValues={
                                ':current_time': int(time.time())
                            }
                        )
                    )
                    logger.debug(f"Cached value in DynamoDB with cache_key: {cache_key}")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                        logger.warning(f"Item with query_id {value['query_id']} already exists and TTL not expired.")
                    else:
                        logger.error(f"Failed to cache item in DynamoDB: {e.response['Error']['Message']}")
                        raise
                except Exception as e:
                    logger.error(f"Unexpected error during put_item operation: {str(e)}")
                    raise

    @staticmethod
    async def get(query_text: str) -> Optional[dict]:
        """
        Get a value from the cache.
        
        Args:
            query_text (str): The original query text.
        
        Returns:
            Optional[dict]: The cached data if found, else None.
        """
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
                            IndexName='cache_key-index',  # Ensure this GSI exists
                            KeyConditionExpression='cache_key = :ck',
                            ExpressionAttributeValues={
                                ':ck': {'S': cache_key}
                            },
                            Limit=1
                        )
                    )
                    logger.debug(f"DynamoDB response: {response}")
                    items = response.get('Items', [])
                    if items:
                        logger.debug(f"Cache hit in DynamoDB for cache_key: {cache_key}")
                        # Convert DynamoDB item to a regular dict
                        return Cache._convert_from_dynamodb_item(items[0])
                    else:
                        logger.debug(f"Cache miss in DynamoDB for cache_key: {cache_key}")
                except ClientError as e:
                    logger.error(f"Failed to get item from DynamoDB cache: {e.response['Error']['Message']}")
                except Exception as e:
                    logger.error(f"Unexpected error during get operation: {str(e)}")
        return None

    @staticmethod
    async def delete(query_text: str):
        """
        Delete a value from the cache.
        
        Args:
            query_text (str): The original query text.
        """
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
                    # Query to get all items with the given cache_key
                    response = await loop.run_in_executor(
                        executor,
                        partial(
                            dynamodb_client.query,
                            TableName=CACHE_TABLE_NAME,
                            IndexName='cache_key-index',  # Ensure this GSI exists
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
                                try:
                                    await loop.run_in_executor(
                                        executor,
                                        partial(table.delete_item, Key={'query_id': query_id, 'cache_key': cache_key})
                                    )
                                    logger.debug(f"Deleted cache entry in DynamoDB for query_id: {query_id}")
                                except ClientError as e:
                                    logger.error(f"Failed to delete item with query_id {query_id}: {e.response['Error']['Message']}")
                                except Exception as e:
                                    logger.error(f"Unexpected error deleting item with query_id {query_id}: {str(e)}")
                    else:
                        logger.debug(f"No cache entry to delete in DynamoDB for cache_key: {cache_key}")
                except ClientError as e:
                    logger.error(f"Failed to query items for deletion in DynamoDB: {e.response['Error']['Message']}")
                except Exception as e:
                    logger.error(f"Unexpected error during delete operation: {str(e)}")

    @staticmethod
    def _convert_to_dynamodb_item(item: dict) -> dict:
        """
        Convert a regular Python dict to a DynamoDB-compatible item.
        
        Args:
            item (dict): The item to convert.
        
        Returns:
            dict: DynamoDB-compatible item.
        """
        dynamodb_item = {}
        for key, value in item.items():
            if isinstance(value, str):
                dynamodb_item[key] = {'S': value}
            elif isinstance(value, int) or isinstance(value, float):
                dynamodb_item[key] = {'N': str(value)}
            elif isinstance(value, bool):
                dynamodb_item[key] = {'BOOL': value}
            elif isinstance(value, list):
                dynamodb_item[key] = {'L': [{'S': str(v)} if isinstance(v, str) else {'N': str(v)} for v in value]}
            elif isinstance(value, dict):
                dynamodb_item[key] = {'M': Cache._convert_to_dynamodb_item(value)}
            else:
                # Handle other types as needed
                dynamodb_item[key] = {'S': str(value)}
        return dynamodb_item

    @staticmethod
    def _convert_from_dynamodb_item(dynamodb_item: dict) -> dict:
        """
        Convert a DynamoDB item to a regular Python dict.
        
        Args:
            dynamodb_item (dict): The DynamoDB item to convert.
        
        Returns:
            dict: Regular Python dictionary.
        """
        converted = {}
        for key, value in dynamodb_item.items():
            for dtype, val in value.items():
                if dtype == 'S':
                    converted[key] = val
                elif dtype == 'N':
                    # Attempt to convert to int, else float
                    if '.' in val:
                        converted[key] = float(val)
                    else:
                        converted[key] = int(val)
                elif dtype == 'BOOL':
                    converted[key] = val
                elif dtype == 'L':
                    converted[key] = [Cache._convert_from_dynamodb_item(v) if isinstance(v, dict) else v for v in val]
                elif dtype == 'M':
                    converted[key] = Cache._convert_from_dynamodb_item(val)
                # Add more types as needed
        return converted
