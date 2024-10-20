# src/handlers/api_handler.py
import os
import uvicorn
import boto3
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mangum import Mangum

# Import from shared_libs
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.provider_utils import load_llm_provider
from shared_libs.utils.logger import Logger
from shared_libs.utils.cache import Cache
import sys
# Add parent directory to the sys.path to access shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import internal model
from models.query_model import QueryModel
from services.query_rag import query_rag

# Initialize logger
logger = Logger(__name__)

# Environment variables
WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", "RagWorker")

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
    logger.info(f"Fetching query with ID: {query_id}")
    query = QueryModel.get_item(query_id)
    if query:
        return query
    logger.log_warning(f"Query not found for ID: {query_id}")
    raise HTTPException(status_code=404, detail="Query not found")

@app.post("/submit_query")
def submit_query_endpoint(request: SubmitQueryRequest):
    try:
        query_text = request.query_text
        logger.info(f"Received submit query request: {query_text}")

        # Check the cache first
        cached_response = Cache.get(query_text)
        if cached_response:
            logger.info(f"Cache hit for query: {query_text}")
            return cached_response

        # Create a new QueryModel item
        new_query = QueryModel(query_text=query_text)
        logger.debug(f"Created new QueryModel: {new_query.dict()}")

        if WORKER_LAMBDA_NAME:
            # Make an async call to the worker Lambda
            try:
                new_query.put_item()  # Save initial query item to the database
                invoke_worker(new_query)
                logger.info("Worker Lambda invoked asynchronously")
            except Exception as e:
                logger.error(f"Error invoking worker Lambda: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to invoke worker Lambda")
        else:
            # Handle the RAG processing directly (useful for local development)
            logger.info("Processing query locally")
            query_response = query_rag(query_text, llm_provider)  # Use the LLM provider loaded from the utility
            new_query.answer_text = query_response.response_text
            new_query.sources = query_response.sources
            new_query.is_complete = True
            new_query.put_item()

            # Cache the response for future queries
            response_data = new_query.dict()
            Cache.set(query_text, response_data)
            logger.info("Query processed and cached locally")

        return new_query.dict()  # Return a dictionary to ensure compatibility with FastAPI response format
    except Exception as exc:
        logger.error(f"Failed to handle submit_query endpoint: {str(exc)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

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
        logger.info("Worker Lambda invoked")
    except Exception as e:
        logger.error(f"Failed to invoke worker Lambda: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to invoke worker Lambda")

# Local Development Function to Test API Endpoints
if __name__ == "__main__":
    # For local development testing
    port = 8000
    logger.info(f"Running the FastAPI server on port {port}.")
    uvicorn.run("handlers.api_handler:app", host="127.0.0.1", port=port)

# Add a local testing endpoint for convenience
@app.post("/local_test_submit_query")
def local_test_submit_query(request: SubmitQueryRequest):
    """
    This endpoint is for local testing only. It allows you to submit a query
    and get an immediate response without relying on the worker Lambda.
    """
    query_text = request.query_text
    logger.info("Local testing endpoint called")

    # Check the cache for the query
    cached_response = Cache.get(query_text)
    if cached_response:
        logger.info("Cache hit during local testing")
        return cached_response

    # Process the query using RAG (local)
    query_response = query_rag(query_text, llm_provider)
    response_data = {
        "query_text": query_text,
        "response_text": query_response.response_text,
        "sources": query_response.sources,
    }

    # Store response in cache
    Cache.set(query_text, response_data)
    logger.info("Query processed and cached during local testing")

    return response_data
