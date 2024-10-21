# shared_libs/utils/cache.py
import os
import redis
import json
import boto3
import time
import hashlib
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
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
s3 = boto3.client("s3", region_name=AWS_REGION)

# Define cache_table after ensuring it exists
try:
    cache_table = dynamodb.Table(CACHE_TABLE_NAME)
    # Attempt to load the table to ensure it's accessible
    cache_table.load()  # This will raise an error if the table does not exist
except ClientError as e:
    if e.response['Error']['Code'] == 'ResourceNotFoundException':
        print(f"DynamoDB table '{CACHE_TABLE_NAME}' not found.")
        raise
    else:
        print(f"Unexpected error accessing DynamoDB: {e}")
        raise


class Cache:
    @staticmethod
    def _generate_cache_key(key: str) -> str:
        """Generate a consistent cache key by hashing the query text."""
        return hashlib.md5(key.encode('utf-8')).hexdigest()

    @staticmethod
    def set(key: str, value: dict, expiry: int = 3600):
        """Set a value in Redis or DynamoDB with an optional expiry time."""
        cache_key = Cache._generate_cache_key(key)
        value_str = json.dumps(value)

        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            try:
                if cache_client:
                    cache_client.set(cache_key, value_str, ex=expiry)  # Use cache_key here
            except redis.RedisError as e:
                print(f"Error setting item in Redis cache: {e}")
        else:
            # Production mode: Use DynamoDB with optional S3 for larger values
            try:
                if len(value_str.encode('utf-8')) > 400 * 1024:  # If > 400KB, store in S3
                    s3_key = f"cache/{cache_key}-{int(time.time())}.json"
                    s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=value_str)
                    value_to_store = {
                        'cache_key': cache_key,
                        's3_key': s3_key,
                        'expires_at': int(time.time()) + expiry
                    }
                else:
                    value_to_store = {
                        'cache_key': cache_key,
                        'cache_value': value_str,
                        'expires_at': int(time.time()) + expiry
                    }
                cache_table.put_item(Item=value_to_store)
            except ClientError as e:
                print(f"Error setting item in DynamoDB cache: {e.response['Error']['Message']}")


    @staticmethod
    def get(key: str) -> Optional[dict]:
        """Get a value from Redis or DynamoDB."""
        cache_key = Cache._generate_cache_key(key)

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
            try:
                response = cache_table.get_item(Key={'cache_key': cache_key})
                if 'Item' in response:
                    item = response['Item']
                    if int(time.time()) > item.get('expires_at', 0):  # Check expiration
                        print(f"Item expired for cache key: {cache_key}")
                        return None
                    
                    if 'cache_value' in item:
                            try:
                                return json.loads(item['cache_value'])
                            except json.JSONDecodeError as e:
                                print(f"Error decoding JSON from DynamoDB cache_value: {e}")
                                return None
                    elif 's3_key' in item:
                            try:
                                s3_key = item['s3_key']
                                s3_response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                                s3_content = s3_response['Body'].read().decode('utf-8')
                                return json.loads(s3_content)
                            except (ClientError, json.JSONDecodeError) as e:
                                print(f"Error retrieving or decoding data from S3: {e}")
                                return None
            except ClientError as e:
                print(f"Error getting item from DynamoDB cache: {e.response['Error']['Message']}")
            return None

    @staticmethod
    def delete(key: str):
        """Delete a value from Redis or DynamoDB."""
        cache_key = Cache._generate_cache_key(key)  # Corrected key generation
        if DEVELOPMENT_MODE:
            try:
                if cache_client:
                    cache_client.delete(cache_key)
            except redis.RedisError as e:
                print(f"Error deleting item from Redis cache: {e}")
        else:
            try:
                response = cache_table.get_item(Key={'cache_key': cache_key})
                if 'Item' in response:
                    item = response['Item']
                    if 's3_key' in item:
                        s3_key = item['s3_key']
                        s3.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                cache_table.delete_item(Key={'cache_key': cache_key})
            except ClientError as e:
                print(f"Error deleting item from DynamoDB cache: {e.response['Error']['Message']}")
