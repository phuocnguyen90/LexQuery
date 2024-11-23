# src/services/qdrant_uploader.py

import uuid
from typing import List,Iterator
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

import boto3
from botocore.exceptions import ClientError

from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.utils.logger import Logger
from shared_libs.models.record_model import Record
from shared_libs.embeddings.embedder_factory import EmbedderFactory # Updated import
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.models.embed_models import EmbeddingRequest, EmbeddingResponse

# Load configuration from shared_libs
config = AppConfigLoader()

embedding_config=EmbeddingConfig.from_config_loader()

# Configure logging using Logger from shared_libs
logger = Logger.get_logger(module_name=__name__)

# Load Qdrant configuration
qdrant_config = config.get("qdrant", {})
QDRANT_API_KEY = qdrant_config.get("api_key")
QDRANT_URL = qdrant_config.get("url")
COLLECTION_NAME = 'legal_qa'

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
embedding_function = EmbedderFactory.create_embedder(embedding_config.library_providers['local'])

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

import json
def load_jsonl(file_path: str) -> List[Record]:
    """
    Load records from a JSONL file with UTF-8 encoding.

    :param file_path: Path to the JSONL file.
    :return: List of Record objects.
    """
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                data = json.loads(line)
                record = Record(**data)  # Assuming Record model has a compatible constructor
                records.append(record)
    except UnicodeDecodeError as e:
        logger.error(f"Failed to decode JSONL file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Failed to load JSONL file {file_path}: {e}")
    return records

def load_jsonl_in_batches(file_path: str, batch_size: int) -> Iterator[List[Record]]:
    """
    Generator to load records from a JSONL file in batches.

    :param file_path: Path to the JSONL file.
    :param batch_size: Number of records per batch.
    :return: Iterator of lists of Record objects.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            batch = []
            for line_number, line in enumerate(file, start=1):
                try:
                    data = json.loads(line)
                    record = Record(**data)  # Assuming Record model has a compatible constructor
                    batch.append(record)
                    if len(batch) == batch_size:
                        yield batch
                        batch = []
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error in line {line_number}: {e}")
                except Exception as e:
                    logger.error(f"Error parsing line {line_number}: {e}")
            if batch:
                yield batch
    except UnicodeDecodeError as e:
        logger.error(f"Failed to decode JSONL file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Failed to load JSONL file {file_path}: {e}")

def get_existing_record_ids(record_ids: List[str]) -> List[str]:
    """
    Retrieve existing record IDs from Qdrant based on payload.record_id.

    :param record_ids: List of record IDs to check.
    :return: List of record IDs that already exist in Qdrant.
    """
    existing_ids = []
    try:
        # Qdrant's filtering allows combining multiple record_ids
        # We'll batch the queries to handle large lists efficiently
        query_batch_size = 100  # Adjust based on performance and Qdrant limits
        for i in range(0, len(record_ids), query_batch_size):
            batch = record_ids[i:i + query_batch_size]
            # Construct a filter to match any of the record_ids in the batch
            filter = qdrant_models.Filter(
                should=[
                    qdrant_models.FieldCondition(
                        key="record_id",
                        match=qdrant_models.MatchValue(value=record_id)
                    ) for record_id in batch
                ],
                minimum_should_match=1
            )
            response = qdrant_client.scroll(
                collection_name=COLLECTION_NAME,
                filter=filter,
                limit=len(batch)  # Number of records expected
            )
            # Extract existing record_ids from the response
            for point in response:
                if 'record_id' in point.payload:
                    existing_ids.append(point.payload['record_id'])
        logger.debug(f"Found {len(existing_ids)} existing records out of {len(record_ids)} queried.")
    except Exception as e:
        logger.error(f"Failed to retrieve existing record IDs from Qdrant: {e}")
    return existing_ids

def add_records_from_jsonl(file_path: str, batch_size: int = 100):
    """
    Add records from a JSONL file to Qdrant in batches, avoiding overwriting existing records.

    :param file_path: Path to the JSONL file.
    :param batch_size: Number of records to process per batch.
    """
    total_uploaded = 0
    total_skipped = 0
    total_records = 0

    logger.info(f"Starting upload process for file: {file_path} with batch size: {batch_size}")

    for batch_number, records in enumerate(load_jsonl_in_batches(file_path, batch_size), start=1):
        batch_size_actual = len(records)
        total_records += batch_size_actual
        record_ids = [record.record_id for record in records]

        # Retrieve existing record IDs in Qdrant
        existing_ids = get_existing_record_ids(record_ids)

        # Determine new records to upload
        new_records = [record for record in records if record.record_id not in existing_ids]
        skipped = len(records) - len(new_records)
        total_skipped += skipped

        if not new_records:
            logger.info(f"Batch {batch_number}: All {batch_size_actual} records already exist. Skipping upload.")
            continue

        logger.info(f"Batch {batch_number}: {len(new_records)} new records to upload, {skipped} skipped.")

        # Batch embed the new records' content
        texts = [record.content for record in new_records]
        embeddings = embedding_function.batch_embed(texts)

        # Prepare records with embeddings
        records_with_embeddings = []
        for record, embedding in zip(new_records, embeddings):
            if not embedding:
                logger.error(f"Skipping record {record.record_id} due to embedding failure.")
                continue
            records_with_embeddings.append(record)

        # Use the existing batch upload method
        add_records_to_qdrant(records_with_embeddings)
        total_uploaded += len(records_with_embeddings)

        logger.info(f"Batch {batch_number}: Uploaded {len(records_with_embeddings)} records. Skipped {skipped} existing records.")

    logger.info(f"Upload complete: {total_uploaded} records uploaded, {total_skipped} records skipped, out of {total_records} total records.")


def validate_jsonl(file_path: str):
    """
    Validate a JSONL file for formatting errors.

    :param file_path: Path to the JSONL file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            for i, line in enumerate(file, start=1):
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"Error in line {i}: {e}")
    except Exception as e:
        logger.error(f"Failed to validate JSONL file {file_path}: {e}")



if __name__ == "__main__":
    import argparse
    import os
    import sys
    file_path=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\preprocessed\preprocessed_data.jsonl'

    parser = argparse.ArgumentParser(description="Upload records from a JSONL file to Qdrant.")
    parser.add_argument("file_path", type=str, help="Path to the JSONL file.")
    parser.add_argument("--batch_size", type=int, default=100, help="Number of records to process per batch.")
    parser.add_argument("--validate", action="store_true", help="Validate the JSONL file before uploading.")
    args = parser.parse_args()

    if not os.path.isfile(args.file_path):
        logger.error(f"File not found: {args.file_path}")
        sys.exit(1)
    if args.validate:
        validate_jsonl(args.file_path)


    add_records_from_jsonl(args.file_path, batch_size=args.batch_size)