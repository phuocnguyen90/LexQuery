import os
import time
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
from shared_libs.utils.cache import Cache
from shared_libs.utils.provider_utils import load_llm_provider
import sys

# Add parent directory to the sys.path to access shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.query_model import QueryModel
from services.query_rag import query_rag

# Initialize the logger
logger = Logger(__name__)

# Load configuration and LLM provider
config = ConfigLoader()
llm_provider = load_llm_provider()

# Cache TTL for responses
CACHE_TTL = 1800  # 30 minutes

def handler(event, context):
    """
    AWS Lambda Handler for the worker function.
    """
    try:
        # Create QueryModel instance from incoming event
        query_item = QueryModel(**event)
        logger.info("Received query", {"query_text": query_item.query_text})

        # Invoke RAG process for the query
        response = invoke_rag(query_item)

        return response.dict()
    except Exception as e:
        logger.error("Failed to process the query", {"error": str(e), "event": event})
        raise e

def invoke_rag(query_item: QueryModel):
    """
    Handles RAG process by checking cache, invoking the RAG model, and saving the result.

    :param query_item: QueryModel instance containing the query text.
    :return: Updated QueryModel instance with the answer.
    """
    query_text = query_item.query_text

    # Step 1: Check Cache for Existing Response
    cached_response = Cache.get(query_text)
    if cached_response:
        logger.info("Cache hit for query", {"query_text": query_text})

        # Check if response_text is valid in cache
        if cached_response.get("response_text"):
            logger.info("Returning cached response", {"query_text": query_text})
            return QueryModel(**cached_response)
        else:
            logger.warning("Cache hit but response_text is missing. Proceeding to generate a new response.", {"query_text": query_text})

    # Step 2: No valid cache found or no response in cached data - Proceed with RAG
    logger.info("No valid cache found, invoking RAG", {"query_text": query_text})
    rag_response = query_rag(query_text, provider=llm_provider)

    # Step 3: Update the QueryModel object with response
    query_item.answer_text = rag_response.response_text
    query_item.sources = rag_response.sources
    query_item.is_complete = bool(rag_response.response_text)

    # Step 4: Cache the response for future queries (only if we have a valid response)
    if query_item.answer_text:
        cache_data = query_item.dict()
        cache_data["timestamp"] = int(time.time())  # Add a timestamp for TTL tracking
        Cache.set(query_item.query_text, cache_data, expiry=CACHE_TTL)
        logger.debug("Cached response for future use", {"query_text": query_item.query_text})
    else:
        logger.warning("Incomplete response, not caching", {"query_text": query_item.query_text})

    # Step 5: Store result in DynamoDB (only if processing is complete)
    if query_item.is_complete:
        try:
            query_item.put_item()
            logger.debug("Query processed and stored successfully", {"query_text": query_item.query_text})
        except Exception as e:
            logger.error("Failed to store the processed query in DynamoDB", {"query_text": query_item.query_text, "error": str(e)})

    return query_item

def main():
    """
    For local testing.
    """
    logger.info("Running example RAG call.")
    query_item = QueryModel(
        query_text="thủ tục thay đổi người thừa kế?"
    )
    response = invoke_rag(query_item)
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing.
    main()
