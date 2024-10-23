# rag_service\src\handlers\work_handler.py
import os
import time
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.logger import Logger
from shared_libs.utils.cache import Cache
from shared_libs.utils.provider_utils import load_llm_provider
import sys
import json
import asyncio
# Add parent directory to the sys.path to access shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.query_model import QueryModel
from services.query_rag import query_rag

# Initialize the logger
logger = Logger().get_logger(module_name=__name__)

# Load configuration and LLM provider
config = ConfigLoader()
llm_provider = load_llm_provider()

# Cache TTL for responses
CACHE_TTL = 1800  # 30 minutes

def handler(event, context):
    for record in event['Records']:
        try:
            payload = json.loads(record['body'])
            query_id = payload.get('query_id')
            if not query_id:
                logger.error("No query_id found in payload.")
                continue  # Skip processing if no query_id

            query_item = QueryModel.get_item(query_id)
            if not query_item:
                logger.error(f"No query found in database for query_id: {query_id}")
                continue

            # Invoke RAG processing with cache handling
            query_item = invoke_rag(query_item)

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Optionally, handle retries or dead-letter queue



async def invoke_rag(query_item: QueryModel):
    """
    Handles RAG process by checking cache, invoking the RAG model, and saving the result.

    :param query_item: QueryModel instance containing the query text.
    :return: Updated QueryModel instance with the answer.
    """
    query_text = query_item.query_text
    normalized_query = query_text.strip().lower()


    # Step 1: Check Cache for Existing Response
    try:
        cached_response = await Cache.get(normalized_query)
        if cached_response:
            if "answer_text" in cached_response and cached_response["answer_text"]:
                query_item.answer_text = cached_response["answer_text"]
                query_item.sources = cached_response.get("sources", [])
                query_item.is_complete = True
                return query_item
            else:
                await Cache.delete(normalized_query)  # Remove incomplete entries
    except Exception as e:
        logger.error(f"Cache retrieval failed for query: {query_text}, error: {str(e)}")

    except Exception as e:
        logger.error(f"Cache retrieval failed for query: {query_text}, error: {str(e)}")

    # Step 2: No valid cache found - Proceed with RAG
    rag_response = await query_rag(query_text)

    # Step 3: Update the QueryModel object with response
    query_item.answer_text = rag_response.response_text
    query_item.sources = rag_response.sources
    query_item.is_complete = True

    # Step 4: Cache the response
    cache_data = {
        "query_id": query_item.query_id,
        "query_text": query_item.query_text,
        "answer_text": query_item.answer_text,
        "sources": query_item.sources,
        "is_complete": query_item.is_complete,
    }
    try:
        await Cache.set(query_text, cache_data, expiry=CACHE_TTL)
        logger.info("Cached response: {}".format(cache_data.get('answer_text')))        
    except Exception as e:
        logger.error(f"Failed to cache response for query: {query_text}, error: {str(e)}")

    return query_item



async def main():
    """
    For local testing.
    """
    logger.info("Running example RAG call.")
    query_item = QueryModel(
        query_text="Quy trình đăng ký hộ kinh doanh tại Việt Nam là gì?"
    )
    
    # Since invoke_rag is an async function, we need to await its result.
    response = await invoke_rag(query_item)
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing: use asyncio.run to execute the async main function.
    asyncio.run(main())