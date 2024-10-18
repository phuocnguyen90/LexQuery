# src/model/query_model.py
import os
import boto3
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import uuid
import json
from pathlib import Path

# Environment variables
TABLE_NAME = os.environ.get("TABLE_NAME", "YourTableName")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False") == "True"
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# DynamoDB setup for production mode
if not DEVELOPMENT_MODE:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)

# Local file setup for development mode
LOCAL_STORAGE_DIR = Path("local_data")
LOCAL_STORAGE_DIR.mkdir(exist_ok=True)
LOCAL_QUERY_FILE = LOCAL_STORAGE_DIR / "query_data.json"

class QueryModel(BaseModel):
    query_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    create_time: int = Field(default_factory=lambda: int(time.time()))
    query_text: str
    answer_text: Optional[str] = None
    sources: List[str] = Field(default_factory=list)
    is_complete: bool = False

    @classmethod
    def get_table(cls):
        if DEVELOPMENT_MODE:
            print("Development mode: Skipping DynamoDB table access.")
            return None
        return dynamodb.Table(TABLE_NAME)

    def put_item(self):
        if DEVELOPMENT_MODE:
            # Save to local JSON file
            self.save_to_local()
        else:
            # Save to DynamoDB
            item = self.as_ddb_item()
            try:
                response = QueryModel.get_table().put_item(Item=item)
                print(response)
            except Exception as e:
                print("ClientError", e)
                raise e

    def save_to_local(self):
        """Save the current query model to a local JSON file for development mode."""
        try:
            # Load existing data if available
            if LOCAL_QUERY_FILE.exists():
                with LOCAL_QUERY_FILE.open('r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []

            # Append the new query data
            data.append(self.dict())

            # Write updated data back to the local file
            with LOCAL_QUERY_FILE.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            print(f"Query data saved locally: {self.query_id}")
        except Exception as e:
            print(f"Failed to save query locally: {str(e)}")

    @classmethod
    def get_item(cls, query_id: str):
        if DEVELOPMENT_MODE:
            # Retrieve from local JSON file
            return cls.load_from_local(query_id)
        else:
            # Retrieve from DynamoDB
            try:
                response = cls.get_table().get_item(Key={"query_id": query_id})
                if "Item" in response:
                    return cls(**response["Item"])
                else:
                    return None
            except Exception as e:
                print("ClientError", e)
                return None

    @classmethod
    def load_from_local(cls, query_id: str):
        """Load a specific query model from the local JSON file for development mode."""
        try:
            if LOCAL_QUERY_FILE.exists():
                with LOCAL_QUERY_FILE.open('r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        if item.get("query_id") == query_id:
                            return cls(**item)
            print(f"No local data found for query_id: {query_id}")
            return None
        except Exception as e:
            print(f"Failed to load query locally: {str(e)}")
            return None

    def as_ddb_item(self):
        """Convert the query model to a format suitable for DynamoDB."""
        return {k: v for k, v in self.dict().items() if v is not None}
