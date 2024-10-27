# src/services/qdrant_uploader.py

import uuid
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

import boto3
from botocore.exceptions import ClientError

from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
from shared_libs.models.record_model import Record
from services.get_embedding_function import get_embedding_function  # Updated import

# Load configuration from shared_libs
config = ConfigLoader()

# Configure logging using Logger from shared_libs
logger = Logger.get_logger(module_name=__name__)

# Load Qdrant configuration
qdrant_config = config.get("qdrant", {})
QDRANT_API_KEY = qdrant_config.get("api_key")
QDRANT_URL = qdrant_config.get("url")
COLLECTION_NAME = 'LEGAL_DB'

# Set up Qdrant Client with Qdrant Cloud parameters
if not QDRANT_API_KEY or not QDRANT_URL:
    logger.error("QDRANT_API_KEY and QDRANT_URL must be set.")
    exit(1)

qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=True  # Optional, faster if using gRPC protocol, but make sure Qdrant Cloud supports it
)

# Initialize the embedding function using Bedrock
embedding_function = get_embedding_function()

def add_record_to_qdrant(record: Record):
    """
    Add a single Record to Qdrant.

    :param record: Record object to be added.
    """
    try:
        # Use the embedding function to get the embedding
        embedding = embedding_function.embed(record.content)
        if not embedding:
            logger.error(f"Skipping record {record.record_id} due to embedding failure.")
            return

        # Use record_id directly as the point ID
        record_id_str = record.record_id

        # Upload to Qdrant
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qdrant_models.PointStruct(
                    id=record_id_str,
                    vector=embedding,
                    payload=record.to_dict()  # Utilize to_dict method from shared_libs Record
                )
            ]
        )
        logger.info(f"Successfully added record {record.record_id} to Qdrant collection '{COLLECTION_NAME}'.")
    except ClientError as e:
        logger.error(f"AWS ClientError while adding record {record.record_id} to Qdrant: {e}")
    except Exception as e:
        logger.error(f"Failed to add record {record.record_id} to Qdrant: {e}")

def add_records_to_qdrant(records: List[Record]):
    """
    Batch add records to Qdrant.

    :param records: List of Record objects to be added.
    """
    points = []
    for record in records:
        embedding = embedding_function.embed(record.content)
        if not embedding:
            logger.error(f"Skipping record {record.record_id} due to embedding failure.")
            continue

        # Generate a separate UUID for Qdrant point ID
        qdrant_uuid = str(uuid.uuid4())

        point = qdrant_models.PointStruct(
            id=qdrant_uuid,
            vector=embedding,
            payload=record.to_dict()  # Utilize to_dict method from shared_libs Record
        )
        points.append(point)

    if points:
        try:
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            logger.info(f"Successfully added {len(points)} records to Qdrant collection '{COLLECTION_NAME}'.")
        except ClientError as e:
            logger.error(f"AWS ClientError while adding records to Qdrant: {e}")
        except Exception as e:
            logger.error(f"Failed to add records to Qdrant: {e}")
