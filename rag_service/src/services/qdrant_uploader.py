# src/services/qdrant_uploader.py

import uuid
from typing import List,Iterator
from qdrant_client.http import models as qdrant_models
from qdrant_client.models import Distance, VectorParams
import os


from shared_libs.utils.logger import Logger
from shared_libs.models.record_model import Record
from shared_libs.embeddings.embedder_factory import EmbedderFactory 
from shared_libs.config import Config
from qdrant_init import initialize_qdrant
from qdrant_utils import ensure_collection_exists, check_duplicate_point


# Load configuration from shared_libs
global_config = Config.load()
embedding_config = global_config.embedding

llm_config = global_config.llm
qdrant_config = global_config.qdrant
factory = EmbedderFactory(embedding_config)

# Configure logging using Logger from shared_libs
logger = Logger.get_logger(module_name="Qdrant Uploader")
logger.debug(embedding_config)


os.environ['ACTIVE_EMBEDDING_PROVIDER'] = 'local'

embedding_function = factory.create_embedder('local')  
from qdrant_init import initialize_qdrant

# Retrieve the expected vector dimension for the provider you are using (e.g., 'local')
expected_dim = embedding_config.load_provider_config('local').get("vector_dimension")
distance_metric = global_config.qdrant.distance_metric
# Retrieve the desired collection name from your config (or use an override)
qa_collection_name = global_config.qdrant.collection_names.get("qa_collection", "legal_qa")
doc_collection_name = global_config.qdrant.collection_names.get("doc_collection", "legal_doc")


# Initialize Qdrant client (default to local for development)
qdrant_client = initialize_qdrant()

def add_record_to_qdrant(record: Record, collection_name: str = qa_collection_name):
    try:
        # Ensure the collection exists (using your existing utility)
        ensure_collection_exists(qdrant_client, collection_name, expected_dim, distance_metric)
        
        # Generate embedding for the record's content.
        embedding = embedding_function.embed(record.content)
        if not embedding:
            logger.error(f"Skipping record {record.record_id} due to embedding failure.")
            return
        
        # Check for duplicate: if a duplicate exists (score >= threshold), skip the upload.
        if check_duplicate_point(qdrant_client, collection_name, embedding, threshold=0.999):
            logger.info(f"Record {record.record_id} is a duplicate; skipping upload.")
            return

        qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                qdrant_models.PointStruct(
                    id=record.record_id,
                    vector=embedding,
                    payload=record.to_dict()
                )
            ]
        )
        logger.info(f"Successfully added record {record.record_id} to collection '{collection_name}'.")
    except Exception as e:
        logger.error(f"Failed to add record {record.record_id} to Qdrant: {e}")
    finally:
        qdrant_client.close()
        logger.info("Qdrant client connection closed.")

def add_records_to_qdrant(records: List[Record], collection_name: str = 'legal_qa', local: bool = True):
    """
    Batch add records to Qdrant. Ensure the collection exists with the correct vector dimension.
    
    :param records: List of Record objects to be added.
    :param local: Whether to use a local Qdrant server.
    """
    # Retrieve the distance metric from the global configuration.
    distance_metric = global_config.qdrant.distance_metric
    # Ensure the target collection exists with the expected vector dimension.
    ensure_collection_exists(qdrant_client, collection_name, expected_dim, distance_metric)
    
    points = []
    for record in records:
        embedding = embedding_function.embed(record.content)
        if not embedding:
            logger.error(f"Skipping record {record.record_id} due to embedding failure.")
            continue

        # Check for duplicates before adding this record.
        if check_duplicate_point(qdrant_client, collection_name, embedding, threshold=0.999):
            logger.info(f"Record {record.record_id} is a duplicate; skipping upload.")
            continue

        # Use record.record_id if available; otherwise, generate a unique ID.
        qdrant_uuid = record.record_id or str(uuid.uuid4())
        point = qdrant_models.PointStruct(
            id=qdrant_uuid,
            vector=embedding,
            payload=record.to_dict()
        )
        points.append(point)

    if points:
        try:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(f"Successfully added {len(points)} records to Qdrant collection '{collection_name}'.")
        except Exception as e:
            logger.error(f"Failed to add records to Qdrant: {e}")
        finally:
            qdrant_client.close()
            logger.info("Qdrant client connection closed.")

    

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
        query_batch_size = 100  # Adjust as needed.
        for i in range(0, len(record_ids), query_batch_size):
            batch = record_ids[i:i + query_batch_size]
            q_filter = qdrant_models.Filter(
                should=[
                    qdrant_models.FieldCondition(
                        key="record_id",
                        match=qdrant_models.MatchValue(value=record_id)
                    ) for record_id in batch
                ]
            )
            # Unpack the tuple (points, next_page_token)
            points, _ = qdrant_client.scroll(
                collection_name=QA_COLLECTION_NAME,
                scroll_filter=q_filter,  # Use the correct parameter name.
                limit=len(batch)
            )
            for point in points:
                if 'record_id' in point.payload:
                    existing_ids.append(point.payload['record_id'])
        logger.debug(f"Found {len(existing_ids)} existing records out of {len(record_ids)} queried.")
    except Exception as e:
        logger.error(f"Failed to retrieve existing record IDs from Qdrant: {e}")
    return existing_ids



def add_records_from_jsonl(file_path: str, batch_size: int = 100, collection_name: str='legal_qa', local:bool=True):
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
        add_records_to_qdrant(records_with_embeddings,collection_name, local)
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
    import sys
    import os
    QA_COLLECTION_NAME = 'legal_qa_768'
    DOC_COLLECTION_NAME='legal_doc_768'

    # Default values for testing in VS Code
    file_path = r"C:\Users\PC\git\legal_qa_rag\format_service\src\data\preprocessed\preprocessed_data.jsonl" 
    batch_size = 100
    use_local = True  # Set to False if you want to use a remote Qdrant server

    # Check if running in a terminal with command-line arguments
    if len(sys.argv) > 1:
        import argparse

        parser = argparse.ArgumentParser(description="Upload records from a JSONL file to Qdrant.")
        parser.add_argument("file_path", type=str, help="Path to the JSONL file.")
        parser.add_argument("--batch_size", type=int, default=100, help="Number of records to process per batch.")
        parser.add_argument("--local", action="store_true", help="Use a local Qdrant server for testing.")
        args = parser.parse_args()

        file_path = args.file_path
        batch_size = args.batch_size
        use_local = args.local

    # Validate the file path
    if not os.path.isfile(file_path):
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    # Reinitialize the Qdrant client based on the `use_local` argument
    qdrant_client = initialize_qdrant()


    # Add records to Qdrant
    add_records_from_jsonl(file_path=file_path, batch_size=batch_size, collection_name=DOC_COLLECTION_NAME ,local=use_local)
