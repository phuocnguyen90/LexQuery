# test rag app
import os
import logging
import fastembed
import numpy as np
import uuid
import json

import re
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from typing import Dict, Any, List


from providers.groq_provider import GroqProvider
from utils.load_config import load_config
from utils.record import Record

# Configure logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load configuration from config.yaml
try:
    config = load_config('src/config/config.yaml')
    logger.info("Configuration loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    exit(1)

# Load environment variables
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")

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

# Ensure the collection exists, otherwise create it
try:
    if qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        # Optionally delete the collection if you need to recreate it
        # qdrant_client.delete_collection(collection_name=COLLECTION_NAME)
        logger.info(f"Qdrant collection '{COLLECTION_NAME}' already exists.")
    else:
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=qdrant_models.VectorParams(size=DIMENSION, distance="Cosine")
        )
        logger.info(f"Qdrant collection '{COLLECTION_NAME}' created with dimension {DIMENSION}.")
except Exception as e:
    logger.error(f"Failed to create or verify Qdrant collection: {e}")
    exit(1)

# Initialize the GroqProvider
try:
    groq_config = {
        'api_key': GROQ_API_KEY,
        'model_name': config.get('groq_model_name', 'llama-3.1-8b-instant'),
        'embedding_model_name': config.get('embedding_model_name', 'groq-embedding-001'),
        'temperature': config.get('temperature', 0.7),
        'max_output_tokens': config.get('max_output_tokens', 4096)
    }
    groq_provider = GroqProvider(config=groq_config, requirements=config.get('requirements', ''))
    logger.info("GroqProvider initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize GroqProvider: {e}")
    exit(1)

# Step 1: Embedding Function using FastEmbed
def fe_embed_text(text: str) -> list:
    """
    Embed a single text using FastEmbed with a small multilingual model.

    :param text: A single text string to embed.
    :return: A list of floats representing the embedding vector.
    """
    try:
        # Initialize the FastEmbed embedding model once
        if not hasattr(fe_embed_text, "embedding_model"):
            fe_embed_text.embedding_model = fastembed.TextEmbedding(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            )
        
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


# Step 4: Function to Perform Vector Search in Qdrant
def search_qdrant(query: str, top_k: int = 3) -> list:
    """
    Search Qdrant using an embedding of the query.

    :param query: The input query to search similar documents.
    :param top_k: Number of similar results to return.
    :return: List of similar documents with 'record_id', 'content', 'source', and 'score'.
    """
    query_embedding = fe_embed_text(query)

    if not query_embedding:
        logger.error("Failed to create a valid embedding for query.")
        return []

    try:
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k
        )
        # Extract 'record_id', 'content', and 'source' from the payload
        return [
            {
                "record_id": hit.payload.get("record_id", ""),
                "content": hit.payload.get("content", ""),
                "source": hit.payload.get("source", ""),
                "score": hit.score
            }
            for hit in search_result
        ]
    except Exception as e:
        logger.error(f"Error searching Qdrant: {e}")
        return []


# Step 5: Validation Function for Citations
def validate_citation(response: str) -> bool:
    """
    Validate that the response contains at least one Document ID citation.

    :param response: The response generated by the LLM.
    :return: True if at least one citation is found, False otherwise.
    """
    pattern = r'\[Mã tài liệu:\s*[\w-]+\]'
    return bool(re.search(pattern, response))


# Step 6: Retrieval-Augmented Generation (RAG) Function
def rag(query: str, groq_provider: GroqProvider) -> str:
    """
    Use Qdrant for retrieval and GroqProvider for augmented generation.

    :param query: The query to generate a response for.
    :param groq_provider: An instance of GroqProvider to interact with the LLM.
    :return: Augmented response from LLM.
    """
    # Step 1: Retrieve similar documents using Qdrant
    retrieved_docs = search_qdrant(query)
    if not retrieved_docs:
        return "Không tìm thấy thông tin liên quan."

    # Step 2: Combine retrieved documents to form context for LLM
    context = "\n\n------------------------------------------------------\n\n".join([
        f"Mã tài liệu: {doc['record_id']}\nNguồn: {doc['source']}\nNội dung: {doc['content']}"
        for doc in retrieved_docs if doc['content']
    ])

    # Step 3: Define the system prompt with clear citation instructions
    system_prompt = '''
    Bạn là một trợ lý pháp lý chuyên nghiệp. Dựa trên câu hỏi của người dùng và các kết quả tìm kiếm liên quan từ cơ sở dữ liệu câu hỏi thường gặp của bạn, hãy trả lời câu hỏi và trích dẫn cơ sở pháp lý nếu có trong thông tin được cung cấp.
    Không thêm ý kiến cá nhân; hãy trả lời chi tiết nhất có thể chỉ sử dụng các kết quả tìm kiếm được cung cấp để trả lời.
    Khi trích dẫn nguồn, hãy tham chiếu đến Mã tài liệu (Record ID) được cung cấp trong ngữ cảnh theo định dạng: [Mã tài liệu: <record_id>].
    Ví dụ: "Theo quy định trong [Mã tài liệu: QA_750F0D91], ...".
    Luôn trả lời bằng tiếng Việt.
    '''

    # Combine system prompt and user message
    full_prompt = f"{system_prompt}\n\nCâu hỏi của người dùng: {query}\n\nCác câu trả lời liên quan:\n\n{context}"

    try:
        # Step 4: Send the prompt to GroqProvider
        answer = groq_provider.send_message(prompt=full_prompt)

        if not answer:
            logger.error("Received empty response from GroqProvider.")
            return "Đã xảy ra lỗi khi tạo câu trả lời."

        # Step 5: Validate that the answer contains at least one citation
        if not validate_citation(answer):
            logger.warning("Câu trả lời không chứa bất kỳ trích dẫn nào từ Mã tài liệu.")
            # Optionally, handle the missing citation, e.g., prompt the LLM again or notify the user
            # For simplicity, we'll return the answer as is
        else:
            logger.info("Câu trả lời chứa các trích dẫn từ Mã tài liệu.")

        return answer
    except Exception as e:
        logger.error(f"Lỗi khi tạo câu trả lời từ RAG: {e}")
        return "Đã xảy ra lỗi khi tạo câu trả lời."

# Example Usage
if __name__ == "__main__":
    # Uncomment the following lines to add documents from a JSONL file
    # jsonl_file_path = r'src\data\preprocessed\preprocessed_data.jsonl'  # Replace with actual path to JSONL file
    # read_and_add_documents(jsonl_file_path)

    # Optionally, test RAG function after records are added
    user_query = "Huy động vốn của công ty cổ phần: Các phương thức và quy định pháp lý?"
    answer = rag(user_query, groq_provider)
    print(f"Answer: {answer}")