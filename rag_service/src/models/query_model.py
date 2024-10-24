# src/model/query_model.py
import os
import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import time
from hashlib import md5
import json
from pathlib import Path
import uuid
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
import aiofiles
import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor
# Environment variables
config = ConfigLoader()

# Initialize logger
logger = Logger.get_logger(module_name=__name__)

CACHE_TABLE_NAME = os.environ.get("CACHE_TABLE_NAME", "CacheTable")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Setup AWS DynamoDB only for production
dynamodb_client = None
dynamodb_resource = None
if not DEVELOPMENT_MODE:
    try:
        dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
        dynamodb_resource = boto3.resource('dynamodb', region_name=AWS_REGION)
        logger.info("Connected to DynamoDB in QueryModel.")
    except ClientError as e:
        logger.error(f"Failed to initialize DynamoDB client: {e.response['Error']['Message']}")
    except Exception as e:
        logger.error(f"Unexpected error initializing DynamoDB client: {str(e)}")

# Local file setup for development mode
LOCAL_STORAGE_DIR = Path("local_data")
LOCAL_STORAGE_DIR.mkdir(exist_ok=True)
LOCAL_QUERY_FILE = LOCAL_STORAGE_DIR / "query_data.json"

# Initialize a ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=3)

def generate_cache_key(query_text: str) -> str:
    normalized_query = query_text.strip().lower()
    return md5(normalized_query.encode('utf-8')).hexdigest()


class QueryModel(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cache_key: str = Field(default_factory=lambda: None)
    create_time: int = Field(default_factory=lambda: int(time.time()))
    query_text: str
    answer_text: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    is_complete: bool = False
    timestamp: Optional[int] = None 
    conversation_history: Optional[List[Dict[str, str]]] = Field(default_factory=list)  # If applicable


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.cache_key:
            self.cache_key = self._generate_cache_key(self.query_text)

    @staticmethod
    def _generate_cache_key(query_text: str) -> str:
        """Generate a consistent cache key by hashing the normalized query text."""
        normalized_key = query_text.strip().lower()
        return md5(normalized_key.encode('utf-8')).hexdigest()


    @classmethod
    async def get_item(cls, query_id: str):
        """Asynchronously retrieve a QueryModel item from DynamoDB."""
        dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
        
        key_schema = {
            'query_id': {'S': query_id},            
        }
        logger.debug(f"Querying DynamoDB Table: {CACHE_TABLE_NAME} with key: {key_schema}")
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                partial(
                    dynamodb_client.query,
                    TableName=CACHE_TABLE_NAME,
                    KeyConditionExpression='query_id = :qid',
                    ExpressionAttributeValues={
                        ':qid': {'S': query_id}
                    },
                    Limit=1  # Optional: if you expect only one item
                )
            )
            items = response.get('Items', [])
            if items:
                item_converted = convert_dynamodb_item(items[0])
                logger.debug(f"Item retrieved successfully from DynamoDB for query_id: {query_id}")
                return cls(**item_converted)
            else:
                logger.warning(f"No item found in DynamoDB for query_id: {query_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving item from DynamoDB: {str(e)}")
            return None


    @classmethod
    async def get_item_by_cache_key(cls, cache_key: str):
        """Asynchronously get an item from DynamoDB by cache_key using GSI."""
        if not dynamodb_client:
            logger.error("DynamoDB client is not initialized.")
            return None
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                partial(
                    dynamodb_client.query,
                    TableName=CACHE_TABLE_NAME,
                    IndexName='cache_key-index',  # Replace with your actual GSI name
                    KeyConditionExpression='cache_key = :ck',
                    ExpressionAttributeValues={
                        ':ck': {'S': cache_key}
                    }
                )
            )
            items = response.get('Items', [])
            if items:
                # Assuming the first item is the desired one
                item_converted = convert_dynamodb_item(items[0])
                logger.debug(f"Item retrieved successfully from DynamoDB for cache_key: {cache_key}")
                return cls(**item_converted)
            else:
                logger.warning(f"No item found in DynamoDB for cache_key: {cache_key}")
                return None
        except ClientError as e:
            logger.error(f"Failed to query DynamoDB by cache_key: {e.response['Error']['Message']}", {"cache_key": cache_key})
            return None
        except Exception as e:
            logger.error(f"Unexpected error during get_item_by_cache_key operation: {str(e)}", {"cache_key": cache_key})
            return None

    async def put_item(self):
        """Asynchronously put the QueryModel item into DynamoDB."""
        dynamodb_resource = boto3.resource('dynamodb', region_name=os.getenv("AWS_REGION", "us-east-1"))
        table_name = os.getenv("CACHE_TABLE_NAME", "CacheTable")
        table = dynamodb_resource.Table(table_name)
        logger.debug(f"Putting item into DynamoDB Table: {table_name} for query_id: {self.query_id}")
        try:
            # Convert the QueryModel to a DynamoDB-compatible dict
            item = self.dict()
            
            await asyncio.get_event_loop().run_in_executor(
                None,
                partial(
                    table.put_item,
                    Item=item,
                    ConditionExpression='attribute_not_exists(is_complete) OR is_complete = :false',
                    ExpressionAttributeValues={
                    ':false': False
                    }
                )
            )
            logger.debug(f"Item put successfully into DynamoDB for query_id: {self.query_id}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning(f"Conditional check failed for query_id: {self.query_id}. Possibly already processed.")
            else:
                logger.error(f"Error putting item into DynamoDB: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Error putting item into DynamoDB: {str(e)}")
            raise

    async def save_to_local(self):
        """Asynchronously save the current query model to a local JSON file."""
        try:
            logger.debug(f"Saving query data locally for query_id: {self.query_id}")
            data = []
            if LOCAL_QUERY_FILE.exists():
                async with aiofiles.open(LOCAL_QUERY_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)

            data.append(self.dict())

            async with aiofiles.open(LOCAL_QUERY_FILE, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2))

            logger.debug(f"Query data saved locally: {self.query_id}")
        except Exception as e:
            logger.error(f"Failed to save query locally: {str(e)}", {"query_id": self.query_id})

    @classmethod
    async def load_from_local(cls, query_id: str):
        """Asynchronously load a specific query model from the local JSON file by query_id."""
        try:
            logger.debug(f"Loading query from local storage for query_id: {query_id}")
            if LOCAL_QUERY_FILE.exists():
                async with aiofiles.open(LOCAL_QUERY_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    for item in data:
                        if item.get("query_id") == query_id:
                            logger.info(f"Query data loaded from local storage for query_id: {query_id}")
                            return cls(**item)
            logger.warning(f"No local data found for query_id: {query_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to load query locally: {str(e)}", {"query_id": query_id})
            return None

    @classmethod
    async def load_from_local_by_cache_key(cls, cache_key: str):
        """Asynchronously load a specific query model from the local JSON file by cache_key."""
        try:
            logger.debug(f"Loading query from local storage for cache_key: {cache_key}")
            if LOCAL_QUERY_FILE.exists():
                async with aiofiles.open(LOCAL_QUERY_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    for item in data:
                        if item.get("cache_key") == cache_key:
                            logger.info(f"Query data loaded from local storage for cache_key: {cache_key}")
                            return cls(**item)
            logger.warning(f"No local data found for cache_key: {cache_key}")
            return None
        except Exception as e:
            logger.error(f"Failed to load query locally: {str(e)}", {"cache_key": cache_key})
            return None

    def as_ddb_item(self):
        """Convert the query model to a DynamoDB-compatible format."""
        logger.debug(f"Converting QueryModel to DynamoDB item format for query_id: {self.query_id}")
        # DynamoDB expects specific data types, ensure correct formatting
        return {
            'query_id': self.query_id,
            'cache_key': self.cache_key,
            'create_time': self.create_time,
            'query_text': self.query_text,
            'answer_text': self.answer_text if self.answer_text else "",
            'sources': self.sources,
            'is_complete': self.is_complete,
            'timestamp':self.timestamp if self.timestamp else 0,
            'conversation_history': self.conversation_history if self.conversation_history else []
        }

def convert_dynamodb_item(item):
    """
    Convert DynamoDB item format to a regular Python dictionary.
    """
    converted = {}
    for key, value in item.items():
        for dtype, val in value.items():
            if dtype == 'S':
                converted[key] = val
            elif dtype == 'N':
                converted[key] = int(val) if val.isdigit() else float(val)
            elif dtype == 'BOOL':
                converted[key] = val
            elif dtype == 'L':
                converted[key] = [convert_dynamodb_item(v) if isinstance(v, dict) else v for v in val]
            elif dtype == 'M':
                converted[key] = convert_dynamodb_item(val)
            # Add more types as needed
    return converted
