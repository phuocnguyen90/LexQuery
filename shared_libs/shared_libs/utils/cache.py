# shared_libs/utils/cache.py
import os
import redis
import json
import time
import hashlib
import aioboto3
from botocore.exceptions import ClientError
from typing import Optional

# Environment Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"

# DynamoDB and S3 Configuration
CACHE_TABLE_NAME = os.getenv("CACHE_TABLE_NAME", "CacheTable")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "legal-rag-qa")
AWS_REGION=os.getenv("AWS_REGION", "us-east-1")
# Initialize Redis connection if in development mode
cache_client = None
if DEVELOPMENT_MODE:
    try:
        cache_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        cache_client.ping()  # Test if Redis is up
    except redis.RedisError as e:
        print(f"Error connecting to Redis: {e}")
        cache_client = None

# Initialize DynamoDB and S3 clients




class Cache:
    @staticmethod
    def _generate_cache_key(key: str) -> str:
        """Generate a consistent cache key by hashing the query text."""
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    @staticmethod
    async def set(cache_key: str, value: dict, expiry: int = 3600):
        """Set a value in Redis or DynamoDB with an optional expiry time."""
        
        value_str = json.dumps(value)
        session = aioboto3.Session()

        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            try:
                if cache_client:
                    cache_client.set(cache_key, value_str, ex=expiry)  # Use cache_key here
            except redis.RedisError as e:
                print(f"Error setting item in Redis cache: {e}")
        else:
            # Production mode: Use DynamoDB with optional S3 for larger values
            async with session.resource('dynamodb', region_name=AWS_REGION) as dynamodb:
                table = await dynamodb.Table(CACHE_TABLE_NAME)
                await table.put_item(Item={**value, 'cache_key': cache_key, 'ttl': int(time.time()) + expiry})
            pass

    @staticmethod
    async def get(cache_key: str) -> Optional[dict]:
        """Get a value from Redis or DynamoDB."""
        session = aioboto3.Session()
        
        

        if DEVELOPMENT_MODE:
            try:
                if cache_client:
                    value = cache_client.get(cache_key)
                    if value:
                        return json.loads(value)
            except redis.RedisError as e:
                print(f"Error getting item from Redis cache: {e}")
            return None
        
        else:
            async with session.resource('dynamodb', region_name=AWS_REGION) as dynamodb:
                table = await dynamodb.Table(CACHE_TABLE_NAME)
                response = await table.get_item(Key={'cache_key': cache_key})
                return response.get('Item')
            pass

    @staticmethod
    async def delete(cache_key: str):
        """Delete a value from Redis or DynamoDB."""
        session = aioboto3.Session()
        async with session.resource('dynamodb', region_name=AWS_REGION) as dynamodb:
            table = await dynamodb.Table(CACHE_TABLE_NAME)
            await table.delete_item(Key={'cache_key': cache_key})
            
    