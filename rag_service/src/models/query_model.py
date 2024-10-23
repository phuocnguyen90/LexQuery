# src/model/query_model.py
import os
import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel, Field
from typing import List, Optional
import time
from hashlib import md5
import json
from pathlib import Path
import uuid
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
import aioboto3
import aiofiles

# Environment variables
config = ConfigLoader()

# Initialize logger
logger = Logger.get_logger(module_name=__name__)

CACHE_TABLE_NAME = os.environ.get("CACHE_TABLE_NAME", "CacheTable")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Setup AWS DynamoDB only for production
dynamodb = None
if not DEVELOPMENT_MODE:
    try:
        dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
        logger.debug(f"DynamoDB resource initialized for region: {AWS_REGION}")
    except Exception as e:
        logger.error(f"Failed to initialize DynamoDB resource: {str(e)}")


# Local file setup for development mode
LOCAL_STORAGE_DIR = Path("local_data")
LOCAL_STORAGE_DIR.mkdir(exist_ok=True)
LOCAL_QUERY_FILE = LOCAL_STORAGE_DIR / "query_data.json"
def generate_cache_key(query_text: str) -> str:
        return md5(query_text.strip().lower().encode('utf-8')).hexdigest()

class QueryModel(BaseModel):
    cache_key: str = Field(default_factory=lambda: None)  # No default generation here
    query_id: str = Field(default=None)
    create_time: int = Field(default_factory=lambda: int(time.time()))
    query_text: str
    answer_text: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    is_complete: bool = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.cache_key:
            # Generate cache_key based on query_text if not already provided
            self.cache_key = generate_cache_key(self.query_text)    

        # Replace cache key generation throughout the workflow with the new utility

    @classmethod
    def get_table(cls):
        if not dynamodb:
            logger.error("DynamoDB resource is not initialized. Ensure that you are running in production mode.")
            raise ValueError("DynamoDB resource not initialized.")
        
        logger.debug(f"Attempting to access DynamoDB table: {CACHE_TABLE_NAME}")
        try:
            table = dynamodb.Table(CACHE_TABLE_NAME)
            logger.debug(f"Successfully accessed DynamoDB table: {CACHE_TABLE_NAME}")
            return table
        except Exception as e:
            logger.error(f"Failed to access DynamoDB table '{CACHE_TABLE_NAME}': {str(e)}")
            raise

    async def put_item(self):
        """Asynchronously put an item into DynamoDB or save locally in development mode."""
        item = self.as_ddb_item()

        if DEVELOPMENT_MODE:
            logger.info("Running in DEVELOPMENT_MODE. Saving item locally instead of DynamoDB.", {"cache_key": self.cache_key})
            await self.save_to_local()
        else:
            try:
                session=aioboto3.Session()
                logger.debug(f"Attempting to put item in DynamoDB for cache_key: {self.cache_key}")
                async with session.resource('dynamodb', region_name=AWS_REGION) as dynamodb:
                    table = await dynamodb.Table(CACHE_TABLE_NAME)
                    response = await table.put_item(Item=item)
                    logger.debug("Successfully put item in DynamoDB", {"query_text": self.query_text, "response": response})
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ResourceNotFoundException':
                    logger.error(f"Table not found: {e.response['Error']['Message']}")
                else:
                    logger.error(f"Failed to put item in DynamoDB: {e.response['Error']['Message']}", {"cache_key": self.cache_key})
                raise
            except Exception as e:
                logger.error(f"Unexpected error during put_item operation: {str(e)}", {"cache_key": self.cache_key})
                raise
            pass

    async def save_to_local(self):
        """Asynchronously save the current query model to a local JSON file."""
        try:
            logger.debug(f"Saving query data locally for cache_key: {self.cache_key}")
            data = []
            if LOCAL_QUERY_FILE.exists():
                async with aiofiles.open(LOCAL_QUERY_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)

            data.append(self.dict())

            async with aiofiles.open(LOCAL_QUERY_FILE, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, indent=2))

            logger.debug(f"Query data saved locally: {self.cache_key}")
        except Exception as e:
            logger.error(f"Failed to save query locally: {str(e)}", {"cache_key": self.cache_key})

    @classmethod
    async def get_item(cls, cache_key: str):
        """Asynchronously get an item from DynamoDB or local storage."""
        if DEVELOPMENT_MODE:
            logger.info(f"Running in DEVELOPMENT_MODE. Retrieving item locally for cache_key: {cache_key}")
            return await cls.load_from_local(cache_key)
        else:
            try:
                session=aioboto3.Session()
                logger.debug(f"Fetching item from DynamoDB for cache_key: {cache_key}")
                async with session.resource('dynamodb', region_name=AWS_REGION) as dynamodb:
                    table = await dynamodb.Table(CACHE_TABLE_NAME)
                    response = await table.get_item(Key={"cache_key": cache_key})
                    if "Item" in response:
                        logger.debug(f"Item retrieved successfully from DynamoDB for cache_key: {cache_key}")
                        return cls(**response["Item"])
                    logger.warning(f"Item not found in DynamoDB for cache_key: {cache_key}")
                    return None
            except ClientError as e:
  
                logger.error(f"Failed to get item from DynamoDB: {e.response['Error']['Message']}", {"cache_key": cache_key})
                return None
            except Exception as e:
                logger.error(f"Unexpected error during get_item operation: {str(e)}", {"cache_key": cache_key})
                return None
            pass

    @classmethod
    async def load_from_local(cls, cache_key: str):
        """Asynchronously load a specific query model from the local JSON file."""
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
        logger.debug(f"Converting QueryModel to DynamoDB item format for cache_key: {self.cache_key}")
        return {k: v for k, v in self.dict().items() if v not in [None, "", [], {}]}
