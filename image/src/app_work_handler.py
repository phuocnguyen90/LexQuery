# src/app_work_handler.py
import os
import sys
import time
from query_model import QueryModel
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.query_rag import query_rag
from utils.provider_utils import get_groq_provider
from utils.load_config import ConfigLoader
from utils.logger import Logger
from utils.cache import Cache

CACHE_TTL = 1800  # 30 minutes
groq_provider=get_groq_provider()

def handler(event, context):
    query_item = QueryModel(**event)
    response = invoke_rag(query_item)
    return response.dict()

def invoke_rag(query_item: QueryModel):
    # Check cache first
    cached_response = Cache.get(query_item.query_text)
    if cached_response:
        Logger.log_event("INFO", "Cache hit", {"query_text": query_item.query_text})
        return cached_response

    # Process the query using RAG
    try:
        rag_response = query_rag(query_item.query_text, groq_provider)
        query_item.answer_text = rag_response.response_text
        query_item.sources = rag_response.sources
        query_item.is_complete = True

        # Store response in cache - including a timestamp for TTL tracking
        cache_data = rag_response.__dict__
        cache_data["timestamp"] = int(time.time())  # Add a timestamp for TTL tracking
        Cache.set(query_item.query_text, cache_data)

        # Store result in DynamoDB (using put_item)
        query_item.put_item()

        # Log the completion event
        Logger.log_event("INFO", "Query processed", {"query_text": query_item.query_text})

        return query_item
    except Exception as e:
        Logger.log_event("ERROR", "Error in processing query", {"query_text": query_item.query_text, "error": str(e)})
        raise e

def main():
    print("Running example RAG call.")
    query_item = QueryModel(
        query_text="chậm nộp thuế thu nhập doanh nghiệp thì bị phạt như thế nào?"
    )
    response = invoke_rag(query_item)
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing.
    main()
