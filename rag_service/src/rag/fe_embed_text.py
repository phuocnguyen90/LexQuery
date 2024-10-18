# src/rag/fe_embed_text.py

import os
import logging
import fastembed
import numpy as np
import uuid
import json

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from typing import Dict, Any, List


from providers.groq_provider import GroqProvider
from utils.load_config import ConfigLoader

from utils.record import Record


# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load configuration from config.yaml
try:
    # Load global configuration
    config = ConfigLoader().get_config()
    logger.info("Configuration loaded successfully.")

except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    exit(1)
# Load settings from configuration
groq_config = config.get('groq', {})
qdrant_config = config.get('qdrant', {})

GROQ_API_KEY = groq_config.get('api_key', os.getenv('GROQ_API_KEY'))
QDRANT_API_KEY = qdrant_config.get('api_key', os.getenv("QDRANT_API_KEY"))
QDRANT_URL = qdrant_config.get('url', os.getenv("QDRANT_URL"))


# Verify that required environment variables are provided
if not QDRANT_API_KEY or not QDRANT_URL:
    logger.error("QDRANT_API_KEY and QDRANT_URL must be set.")
    exit(1)

# Qdrant Collection Configuration
COLLECTION_NAME = "legal_qa"
DIMENSION = 384  # Updated to match the FastEmbed model's output dimension

# Set up Qdrant Client with Qdrant Cloud parameters
qdrant_client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    prefer_grpc=True  # Optional, faster if using gRPC protocol, but make sure Qdrant Cloud supports it
)


def fe_embed_text(text: str) -> list:
    """
    Embed a single text using FastEmbed with a small multilingual model.

    :param text: A single text string to embed.
    :return: A list of floats representing the embedding vector.
    """
    try:
        # Initialize the FastEmbed embedding model once
        if not hasattr(fe_embed_text, "embedding_model"):
            model_name = config.get('embedding', {}).get('model_name', "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            fe_embed_text.embedding_model = fastembed.TextEmbedding(model_name=model_name)
        
        # Obtain the embedding generator
        embedding_generator = fe_embed_text.embedding_model.embed(text)
        
        # Convert the generator to a list and then to a numpy array
        embeddings = list(embedding_generator)
        if not embeddings:
            logger.error(f"No embeddings returned for text '{text}'.")
            return []
        
        embedding = np.array(embeddings)
        
        # Handle 2D arrays with a single embedding vector
        if embedding.ndim == 2 and embedding.shape[0] == 1:
            embedding = embedding[0]
        
        # Ensure that the embedding is a flat array
        if embedding.ndim != 1:
            logger.error(f"Embedding for text '{text}' is not a flat array. Got shape: {embedding.shape}")
            return []
        
        # Log embedding norm for debugging
        embedding_norm = np.linalg.norm(embedding)
        logger.debug(f"Embedding norm for text '{text}': {embedding_norm}")
        
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to create embedding for the input: '{text}', error: {e}")
        return []



# Step 2: Read JSONL File and Create Records
def read_and_add_documents(jsonl_file_path: str):
    """
    Read records from a JSONL file and batch add them to Qdrant.

    :param jsonl_file_path: Path to the JSONL file containing records.
    """
    records_batch = []
    try:
        with open(jsonl_file_path, 'r', encoding='utf-8') as jsonl_file:
            for line in jsonl_file:
                try:
                    data = json.loads(line)
                    # Create a Record instance from JSON
                    record = Record.from_json(data)
                    if record:
                        records_batch.append(record)
                    else:
                        logger.error("Failed to create Record from JSON data.")
                except json.JSONDecodeError as e:
                    logger.error(f"Error reading line from JSONL file: {e}")

                # Define a batch size (e.g., 100 records) to upsert in chunks
                if len(records_batch) >= 100:
                    add_records_to_qdrant(records_batch)
                    records_batch = []

        # Add any remaining records that didn't reach the batch size
        if records_batch:
            add_records_to_qdrant(records_batch)
    except FileNotFoundError:
        logger.error(f"File '{jsonl_file_path}' not found.")
    except Exception as e:
        logger.error(f"Error processing JSONL file: {e}")


def add_record_to_qdrant(record: Record):
    """
    Add a single Record to Qdrant.

    :param record: Record object to be added.
    """
    try:
        embedding = fe_embed_text(record.content)
        if not embedding:
            logger.error(f"Skipping record {record.record_id} due to embedding failure.")
            return

        # Use record_id directly as the point ID
        record_id_str = record.record_id

        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                qdrant_models.PointStruct(
                    id=record_id_str,
                    vector=embedding,
                    payload={
                        "record_id": record.record_id,
                        "document_id": record.document_id,
                        "content": record.content,
                        "title": record.title,
                        "chunk_id": record.chunk_id,
                        "hierarchy_level": record.hierarchy_level,
                        "categories": record.categories,
                        "relationships": record.relationships,
                        "published_date": record.published_date,
                        "source": record.source,
                        "processing_timestamp": record.processing_timestamp,
                        "validation_status": record.validation_status,
                        "language": record.language,
                        "summary": record.summary
                    }
                )
            ]
        )
        logger.info(f"Successfully added record {record.record_id} to Qdrant collection '{COLLECTION_NAME}'.")
    except Exception as e:
        logger.error(f"Failed to add record {record.record_id} to Qdrant: {e}")

# Step 3: Batch Add Records to Qdrant
def add_records_to_qdrant(records: List[Record]):
    """
    Batch add records to Qdrant.

    :param records: List of Record objects to be added.
    """
    points = []
    for record in records:
        embedding = fe_embed_text(record.content)
        if not embedding:
            logger.error(f"Skipping record {record.record_id} due to embedding failure.")
            continue

        # Generate a separate UUID for Qdrant point ID
        qdrant_uuid = str(uuid.uuid4())

        point = qdrant_models.PointStruct(
            id=qdrant_uuid,  # Use generated UUID as the point ID
            vector=embedding,
            payload={
                "record_id": record.record_id,          # Store original record_id
                "document_id": record.document_id,
                "content": record.content,
                "title": record.title,
                "chunk_id": record.chunk_id,
                "hierarchy_level": record.hierarchy_level,
                "categories": record.categories,
                "relationships": record.relationships,
                "published_date": record.published_date,
                "source": record.source,
                "processing_timestamp": record.processing_timestamp,
                "validation_status": record.validation_status,
                "language": record.language,
                "summary": record.summary
            }
        )
        points.append(point)

    if points:
        try:
            qdrant_client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            logger.info(f"Successfully added {len(points)} records to Qdrant collection '{COLLECTION_NAME}'.")
        except Exception as e:
            logger.error(f"Failed to add records to Qdrant: {e}")


