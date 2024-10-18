# src/handlers/api_handler.py
import os
import uvicorn
import boto3
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mangum import Mangum

# Import from shared_libs
from shared_libs.config_loader import ConfigLoader
from shared_libs.utils.provider_utils import load_llm_provider 
from shared_libs.utils.logger import Logger
from shared_libs.utils.cache import Cache

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import internal model
from models.query_model import QueryModel
from services.query_rag import query_rag

# Environment variables
WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", None)

# Load the LLM provider (abstracted utility function handles fallbacks)
llm_provider = load_llm_provider()

# Initialize FastAPI application
app = FastAPI()

# Entry point for AWS Lambda using Mangum
deployment_handler = Mangum(app)

# Data models
class SubmitQueryRequest(BaseModel):
    query_text: str

# API Endpoints
@app.get("/")
def index():
    return {"Hello": "World"}

@app.get("/get_query")
def get_query_endpoint(query_id: str):
    query = QueryModel.get_item(query_id)
    if query:
        return query
    raise HTTPException(status_code=404, detail="Query not found")

@app.post("/submit_query")
def submit_query_endpoint(request: SubmitQueryRequest):
    # Create a new QueryModel item
    new_query = QueryModel(query_text=request.query_text)

    if WORKER_LAMBDA_NAME:
        # Make an async call to the worker Lambda
        new_query.put_item()  # Save initial query item to database
        invoke_worker(new_query)
        Logger.log_event("INFO", "Worker Lambda invoked asynchronously", {"query_text": request.query_text})
    else:
        # Handle the RAG processing directly (useful for local development)
        Logger.log_event("INFO", "Processing query locally", {"query_text": request.query_text})
        query_response = query_rag(request.query_text, llm_provider)  # Use the LLM provider loaded from the utility
        new_query.answer_text = query_response.response_text
        new_query.sources = query_response.sources
        new_query.is_complete = True
        new_query.put_item()

    return new_query.dict()  # Return a dictionary to ensure compatibility with FastAPI response format

def invoke_worker(query: QueryModel):
    # Initialize the Lambda client
    lambda_client = boto3.client("lambda")

    # Get the QueryModel as a dictionary
    payload = query.dict()

    # Invoke the worker Lambda function asynchronously
    try:
        response = lambda_client.invoke(
            FunctionName=WORKER_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        Logger.log_event("INFO", "Worker Lambda invoked", {"response": str(response)})
    except Exception as e:
        Logger.log_event("ERROR", "Error invoking worker Lambda", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to invoke worker Lambda")

# Local Development Function to Test API Endpoints
if __name__ == "__main__":
    # For local development testing
    port = 8000
    print(f"Running the FastAPI server on port {port}.")
    uvicorn.run("handlers.api_handler:app", host="127.0.0.1", port=port)

# Add a local testing endpoint for convenience
@app.post("/local_test_submit_query")
def local_test_submit_query(request: SubmitQueryRequest):
    """
    This endpoint is for local testing only. It allows you to submit a query
    and get an immediate response without relying on the worker Lambda.
    """
    Logger.log_event("INFO", "Local testing endpoint called", {"query_text": request.query_text})

    # Check the cache for the query
    cached_response = Cache.get(request.query_text)
    if cached_response:
        Logger.log_event("INFO", "Cache hit during local testing", {"query_text": request.query_text})
        return cached_response

    # Process the query using RAG (local)
    query_response = query_rag(request.query_text, llm_provider)
    response_data = {
        "query_text": request.query_text,
        "response_text": query_response.response_text,
        "sources": query_response.sources,
    }

    # Store response in cache
    Cache.set(request.query_text, response_data)

    # Log completion
    Logger.log_event("INFO", "Query processed and cached during local testing", {"query_text": request.query_text})

    return response_data
