# src/services/qdrant_uploader.py
import os
import uuid
import json
from typing import List, Iterator, Optional


from qdrant_client.http import models as qmodels


from shared_libs.utils.logger import Logger
from shared_libs.models.record_model import Record
from shared_libs.embeddings.embedder_factory import EmbedderFactory
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig


from .qdrant_init import initialize_qdrant
from .qdrant_utils import ensure_collection_exists, check_duplicate_point


logger = Logger.get_logger(module_name="Qdrant Uploader")



# ---------------------------------------------------------------------------
# Configuration & initialization
# ---------------------------------------------------------------------------
app_config = AppConfigLoader()
embedding_config = EmbeddingConfig.get_embed_config(app_config)
factory = EmbedderFactory(embedding_config)


# Use env override if set; otherwise the default provider from YAML
ACTIVE_PROVIDER = embedding_config.active_provider # e.g., "local_gemma3"
embedder = factory.create_embedder(ACTIVE_PROVIDER)


# Expected vector dimension should match the active provider's config
expected_dim = embedding_config.get_vector_dimension()


# Qdrant settings from master config
_qcfg = app_config.get("qdrant", {}) or {}
collection_names = (_qcfg.get("collection_names", {}) or {})
DISTANCE_METRIC: str = _qcfg.get("distance_metric", "cosine").lower() # "cosine" or "dot"/"dotproduct"
QA_COLLECTION_NAME = collection_names.get("qa_collection", "legal_qa")
DOC_COLLECTION_NAME = collection_names.get("doc_collection", "legal_doc")


# One client for the whole module; do not close per-operation
qdrant_client = initialize_qdrant()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_config_banner():
    logger.info(
    "Embedding provider: %s | dim=%s | qdrant metric=%s | qa=%s | doc=%s",
    ACTIVE_PROVIDER,
    expected_dim,
    DISTANCE_METRIC,
    QA_COLLECTION_NAME,
    DOC_COLLECTION_NAME,
    )




def _ensure_collection(collection_name: str):
    ensure_collection_exists(qdrant_client, collection_name, expected_dim, DISTANCE_METRIC)

# ---------------------------------------------------------------------------
# Single-record upsert
# ---------------------------------------------------------------------------

def add_record_to_qdrant(record: Record, collection_name: Optional[str] = None) -> None:
    """Add a single Record to Qdrant using the active embedder.


    - Ensures collection exists with correct vector size + distance.
    - Skips near-duplicates by vector similarity.
    """
    target_collection = collection_name or QA_COLLECTION_NAME
    try:
        # Ensure the collection exists (using your existing utility)
        _ensure_collection(target_collection)
        
        # Generate embedding for the record's content.
        embedding = embedder.embed(record.content)
        if not embedding:
            logger.error(f"Skipping record {record.record_id} due to embedding failure.")
            return
        
        # Check for duplicate: if a duplicate exists (score >= threshold), skip the upload.
        if check_duplicate_point(qdrant_client, collection_name, embedding, threshold=0.999):
            logger.info(f"Record {record.record_id} is a duplicate; skipping upload.")
            return
        
        # Upsert
        qdrant_client.upsert(
            collection_name=collection_name,
            points=[
                qmodels.PointStruct(
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

# ---------------------------------------------------------------------------
# Batch upsert
# ---------------------------------------------------------------------------

def add_records_to_qdrant(records: List[Record], collection_name: Optional[str] = None) -> None:
    """
    Batch add records to Qdrant. Ensure the collection exists with the correct vector dimension.
    
    :param records: List of Record objects to be added.
    :param local: Whether to use a local Qdrant server.
    """
    if not records:
        return 
    
    target_collection = collection_name or QA_COLLECTION_NAME
    _ensure_collection(target_collection)
    # Compute embeddings in one shot
    texts = [r.content for r in records]
    try:
        embeddings = embedder.batch_embed(texts)
    except Exception as e:
        logger.error("Batch embed failed for %d records: %s", len(records), e)
        return
    # Retrieve the distance metric from the global configuration.
    
    points: List[qmodels.PointStruct] = []
    for rec, vec in zip(records, embeddings):
        if not vec:
            logger.error(f"Skipping record {rec.record_id} due to embedding failure.", rec.record_id)
            continue

        if check_duplicate_point(qdrant_client, target_collection, vec, threshold=0.999):
            logger.info("Record %s is a duplicate; skipping.", rec.record_id)
            continue
        points.append(
            qmodels.PointStruct(
            id=rec.record_id or str(uuid.uuid4()),
            vector=vec,
            payload=rec.to_dict(),
            )
        )

    if not points:
        logger.info("No new points to upsert into '%s'.", target_collection)
        return
    try:
        qdrant_client.upsert(
            collection_name=target_collection,
            points=points
        )
        logger.info("Successfully upserted %d records into '%s'.", len(points), target_collection)
    except Exception as e:
        logger.error("Failed to upsert %d points into '%s': %s", len(points), target_collection, e)
    

# ---------------------------------------------------------------------------
# JSONL IO
# ---------------------------------------------------------------------------
import json
def load_jsonl(file_path: str) -> List[Record]:
    """
    Load records from a JSONL file with UTF-8 encoding.

    :param file_path: Path to the JSONL file.
    :return: List of Record objects.
    """
    records = List[Record] = []
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
            batch: List[Record] = []
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

# ---------------------------------------------------------------------------
# Existence checks
# ---------------------------------------------------------------------------

def get_existing_record_ids(collection_name: str, record_ids: List[str]) -> List[str]:
    """
    Retrieve existing record IDs from Qdrant based on payload.record_id.
    
    :param record_ids: List of record IDs to check.
    :return: List of record IDs that already exist in Qdrant.
    """
    existing: List[str] = []
    try:
        
        if not record_ids:
            return existing
        step = 100
        for i in range(0, len(record_ids), step):
            batch = record_ids[i : i + step]
            q_filter = qmodels.Filter(
                should=[
                qmodels.FieldCondition(
                key="record_id", match=qmodels.MatchValue(value=rid)
                )
                for rid in batch
                ]
            )
            points, _ = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=q_filter,
                limit=len(batch),
                with_vectors=False,
                with_payload=True,
                )
            for p in points:
                rid = p.payload.get("record_id") if isinstance(p.payload, dict) else None
                if rid:
                    existing.append(rid)
        logger.debug("Found %d existing of %d checked in '%s'.", len(existing), len(record_ids), collection_name)
    except Exception as e:
        logger.error("Failed to retrieve existing record IDs from Qdrant: %s", e)
    return existing



# ---------------------------------------------------------------------------
# High-level driver for JSONL -> Qdrant
# ---------------------------------------------------------------------------

def add_records_from_jsonl(
    file_path: str,
    batch_size: int = 100,
    collection_name: Optional[str] = None,
    ) -> None:
    
    """
    Add records from a JSONL file to Qdrant in batches, avoiding overwriting existing records.

    :param file_path: Path to the JSONL file.
    :param batch_size: Number of records to process per batch.
    """
    target_collection = collection_name or QA_COLLECTION_NAME
    _log_config_banner()
    _ensure_collection(target_collection)

    total_uploaded = 0
    total_skipped = 0
    total_records = 0

    logger.info(f"Starting upload process for file: {file_path} with batch size: {batch_size}")

    for batch_number, records in enumerate(load_jsonl_in_batches(file_path, batch_size), start=1):

        total_records += len(records)
        ids = [r.record_id for r in records]

        # Retrieve existing record IDs in Qdrant
        existing_ids = get_existing_record_ids(target_collection, ids)

        # Determine new records to upload
        new_records = [record for record in records if record.record_id not in existing_ids]
        skipped = len(records) - len(new_records)
        total_skipped += skipped

        if not new_records:
            logger.info("Batch %d: all %d records already exist; skipping.", batch_number, len(records))
            continue

        logger.info(f"Batch {batch_number}: {len(new_records)} new records to upload, {skipped} skipped.")

        # Embed and upsert the new records
        add_records_to_qdrant(new_records, target_collection)


        total_uploaded += len(new_records)

        logger.info(
            "Batch %d: uploaded %d; skipped %d existing.", batch_number, len(new_records), skipped
            )

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
    import argparse
    parser = argparse.ArgumentParser(description="Upload records from JSONL to Qdrant.")
    parser.add_argument("file_path", type=str, help="Path to the JSONL file.")
    parser.add_argument("--batch_size", type=int, default=100, help="Number of records per batch.")
    parser.add_argument("--collection", type=str, default=DOC_COLLECTION_NAME, help="Target Qdrant collection name.")
    args = parser.parse_args()
    if not os.path.isfile(args.file_path):
        logger.error("File not found: %s", args.file_path)
        sys.exit(1)


    try:
        add_records_from_jsonl(args.file_path, batch_size=args.batch_size, collection_name=args.collection)
    finally:
        # Close the shared client once at the end of the run
        try:
            qdrant_client.close()
        except Exception:
            pass
        logger.info("Qdrant client connection closed.")

    # Default values for testing in VS Code
    # file_path = r"C:\Users\PC\git\legal_qa_rag\format_service\src\data\raw\qa_data.jsonl" 
    # python -m rag_service.src.services.qdrant_uploader "C:\Users\PC\git\legal_qa_rag\format_service\src\data\raw\qa_data.jsonl" --batch_size 100 --collection legal_doc_768 