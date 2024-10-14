# src/app_work_handler.py
import os
import sys
from query_model import QueryModel

# Properly add src to sys.path if necessary
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.query_rag import query_rag
from utils.provider_utils import get_groq_provider
from utils.load_config import ConfigLoader

# Load the configuration globally so that it persists across invocations if the Lambda container is reused
config = ConfigLoader().get_config()

# Initialize the GroqProvider globally for reusability
groq_provider = get_groq_provider()

def handler(event, context):
    query_item = QueryModel(**event)
    invoke_rag(query_item)

def invoke_rag(query_item: QueryModel):
    rag_response = query_rag(query_item.query_text, groq_provider)
    query_item.answer_text = rag_response.response_text
    query_item.sources = rag_response.sources
    query_item.is_complete = True
    query_item.put_item()
    print(f"✅ Item is updated: {query_item}")
    return query_item

def main():
    print("Running example RAG call.")
    query_item = QueryModel(
        query_text="Huy động vốn của công ty cổ phần: Các phương thức và quy định pháp lý?"
    )
    response = invoke_rag(query_item)
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing.
    main()
