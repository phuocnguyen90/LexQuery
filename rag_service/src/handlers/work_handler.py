# handlers/work_handler.py
import os
import time
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
from shared_libs.utils.cache import Cache
from shared_libs.utils.provider_utils import load_llm_provider
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.query_model import QueryModel
from services.query_rag import query_rag

# Load configuration and LLM provider
config = ConfigLoader()
logger = Logger()
llm_provider = load_llm_provider()

# Cache TTL for responses
CACHE_TTL = 1800  # 30 minutes

def handler(event, context):
    """
    AWS Lambda Handler for the worker function.
    """
    try:
        query_item = QueryModel(**event)
        response = invoke_rag(query_item)
        return response.dict()
    except Exception as e:
        logger.log_error("Failed to process the query", {"error": str(e), "event": event})
        raise e

def invoke_rag(query_item: QueryModel):
    """
    Handles RAG process by checking cache, invoking the RAG model, and saving the result.
    
    :param query_item: QueryModel instance containing the query text.
    :return: Updated QueryModel instance with the answer.
    """
    # Step 1: Check Cache for Existing Response
    cached_response = Cache.get(query_item.query_text)
    if cached_response:
        logger.log_info("Cache hit for query", {"query_text": query_item.query_text})
        return QueryModel(**cached_response)  # Return the cached QueryModel object

    # Step 2: Process the query using RAG
    try:
        logger.log_info("No cache found, invoking RAG", {"query_text": query_item.query_text})
        rag_response = query_rag(query_item.query_text, provider=llm_provider)

        # Step 3: Update the QueryModel object
        query_item.answer_text = rag_response.response_text
        query_item.sources = rag_response.sources
        query_item.is_complete = True

        # Step 4: Cache the response for future queries
        cache_data = query_item.to_dict()
        cache_data["timestamp"] = int(time.time())  # Add a timestamp for TTL tracking
        Cache.set(query_item.query_text, cache_data, expiry=CACHE_TTL)

        # Step 5: Store result in DynamoDB
        query_item.put_item()

        # Step 6: Log the completion event
        logger.log_info("Query processed successfully", {"query_text": query_item.query_text})

        return query_item
    except Exception as e:
        logger.log_error("Error during RAG processing", {"query_text": query_item.query_text, "error": str(e)})
        raise e

def main():
    """
    For local testing.
    """
    logger.log_info("Running example RAG call.")
    query_item = QueryModel(
        query_text="thủ tục thay đổi người đại diện theo pháp luật của doanh nghiệp?"
    )
    response = invoke_rag(query_item)
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing.
    main()
