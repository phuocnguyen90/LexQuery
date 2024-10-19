# shared_libs/utils/cache.py
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

# DynamoDB and S3 Configuration
DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "YourCacheTableName")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-s3-bucket-name")

# Initialize Redis connection if in development mode
cache_client = None
if DEVELOPMENT_MODE:
    cache_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

# Initialize DynamoDB and S3 clients
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Ensure the DynamoDB Table and S3 Bucket are created
def ensure_dynamodb_table_exists():
    try:
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        table.load()  # This will trigger a resource load and fail if the table does not exist
        print(f"DynamoDB table '{DYNAMODB_TABLE_NAME}' already exists.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"DynamoDB table '{DYNAMODB_TABLE_NAME}' not found. Creating a new one.")
            try:
                table = dynamodb.create_table(
                    TableName=DYNAMODB_TABLE_NAME,
                    KeySchema=[
                        {
                            'AttributeName': 'cache_key',
                            'KeyType': 'HASH'  # Partition key
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'cache_key',
                            'AttributeType': 'S'  # String type
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'  # Use on-demand billing
                )
                table.wait_until_exists()  # Wait until the table is created
                print(f"DynamoDB table '{DYNAMODB_TABLE_NAME}' created successfully.")
            except ClientError as create_error:
                print(f"Failed to create DynamoDB table '{DYNAMODB_TABLE_NAME}': {create_error}")
        else:
            print(f"Unexpected error while accessing DynamoDB: {e}")

def ensure_s3_bucket_exists():
    try:
        # Check if the bucket exists by attempting to access its location
        s3.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"S3 bucket '{S3_BUCKET_NAME}' already exists.")
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            print(f"S3 bucket '{S3_BUCKET_NAME}' not found. Creating a new one.")
            try:
                s3.create_bucket(
                    Bucket=S3_BUCKET_NAME,
                    CreateBucketConfiguration={
                        'LocationConstraint': boto3.session.Session().region_name
                    }
                )
                print(f"S3 bucket '{S3_BUCKET_NAME}' created successfully.")
            except ClientError as create_error:
                print(f"Failed to create S3 bucket '{S3_BUCKET_NAME}': {create_error}")
        else:
            print(f"Unexpected error while accessing S3 bucket: {e}")

# Ensure resources exist at the start
ensure_dynamodb_table_exists()
ensure_s3_bucket_exists()

# Define cache_table after ensuring it exists
cache_table = dynamodb.Table(DYNAMODB_TABLE_NAME)

class Cache:
    @staticmethod
    def set(key: str, value: dict, expiry: int = 3600):
        """Set a value in Redis or DynamoDB with an optional expiry time."""
        value_str = json.dumps(value)

        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            try:
                cache_client.set(key, value_str, ex=expiry)
            except redis.RedisError as e:
                print(f"Error setting item in Redis cache: {e}")
        else:
            # Production mode: Use DynamoDB with optional S3 for larger values
            if len(value_str.encode('utf-8')) > 400 * 1024:  # If > 400KB, store in S3
                s3_key = f"cache/{key}-{int(time.time())}.json"
                try:
                    s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=value_str)
                    value_to_store = {
                        'cache_key': key,
                        's3_key': s3_key,
                        'ttl': int(time.time()) + expiry  # Use TTL to auto-expire items in DynamoDB
                    }
                except ClientError as e:
                    print(f"Error setting item in S3 cache: {e}")
                    return
            else:
                value_to_store = {
                    'cache_key': key,
                    'cache_value': value_str,
                    'ttl': int(time.time()) + expiry  # Use TTL to auto-expire items in DynamoDB
                }

            try:
                cache_table.put_item(Item=value_to_store)
            except ClientError as e:
                print(f"Error setting item in DynamoDB cache: {e}")

    @staticmethod
    def get(key: str) -> Optional[dict]:
        """Get a value from Redis or DynamoDB."""
        if DEVELOPMENT_MODE:
            # Use Redis for development mode
            try:
                value = cache_client.get(key)
                if value:
                    return json.loads(value)
            except redis.RedisError as e:
                print(f"Error getting item from Redis cache: {e}")
            return None
        else:
            # Production mode: Use DynamoDB and optionally S3
            try:
                response = cache_table.get_item(Key={'cache_key': key})
                if 'Item' in response:
                    item = response['Item']
                    if 'cache_value' in item:
                        return json.loads(item['cache_value'])
                    elif 's3_key' in item:
                        s3_key = item['s3_key']
                        try:
                            s3_response = s3.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                            s3_content = s3_response['Body'].read().decode('utf-8')
                            return json.loads(s3_content)
                        except ClientError as e:
                            print(f"Error getting item from S3 cache: {e}")
            except ClientError as e:
                print(f"Error getting item from DynamoDB cache: {e}")
            return None

    @staticmethod
    def delete(key: str):
        """Delete a value from Redis or DynamoDB."""
        if DEVELOPMENT_MODE:
            try:
                cache_client.delete(key)
            except redis.RedisError as e:
                print(f"Error deleting item from Redis cache: {e}")
        else:
            try:
                response = cache_table.get_item(Key={'cache_key': key})
                if 'Item' in response:
                    item = response['Item']
                    if 's3_key' in item:
                        s3_key = item['s3_key']
                        try:
                            s3.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                        except ClientError as e:
                            print(f"Error deleting item from S3 cache: {e}")
                cache_table.delete_item(Key={'cache_key': key})
            except ClientError as e:
                print(f"Error deleting item from DynamoDB cache: {e}")
