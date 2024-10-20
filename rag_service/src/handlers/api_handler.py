# src/handlers/api_handler.py
import os
import uvicorn
import boto3
from botocore.exceptions import ClientError
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

config=ConfigLoader()
# Initialize logger
logger = Logger(__name__)

# Environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
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
    logger.warning(f"Query not found for ID: {query_id}")
    raise HTTPException(status_code=404, detail="Query not found")

@app.post("/submit_query")
def submit_query_endpoint(request: SubmitQueryRequest):
    """
    Endpoint for handling query submission. Checks cache, processes using RAG, and caches response.
    """
    try:
        query_text = request.query_text
        logger.info(f"Received submit query request: {query_text}")

        # Step 1: Check Cache for Existing Response
        cached_response = Cache.get(query_text)
        if cached_response:
            logger.info(f"Cache hit for query: {query_text}")
            return cached_response

        # Step 2: Process the Query
        new_query = QueryModel(query_text=query_text)
        if WORKER_LAMBDA_NAME:
            # Make an async call to the worker Lambda (for production use case)
            new_query.put_item()  # Save initial query item to the database
            invoke_worker(new_query)
            logger.info("Worker Lambda invoked asynchronously")
        else:
            # Handle the RAG processing locally (for development use case)
            logger.info("Processing query locally")
            query_response = query_rag(query_text, llm_provider)
            new_query.answer_text = query_response.response_text
            new_query.sources = query_response.sources
            new_query.is_complete = True

            # Step 3: Save the updated query item to the database
            new_query.put_item()
            logger.info(f"Saved processed query to database: {new_query.dict()}")

            # Step 4: Cache the response for future queries
            response_data = new_query.dict()
            Cache.set(query_text, response_data)
            logger.info(f"Query processed and cached locally: {query_text}")

        # Step 5: Return the response
        return new_query.dict()

    except Exception as exc:
        logger.error(f"Failed to handle submit_query endpoint: {str(exc)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


lambda_client = boto3.client("lambda", region_name=AWS_REGION)
ecs_client = boto3.client("ecs", region_name=AWS_REGION)

def invoke_worker(query: QueryModel):
    payload = query.dict()

    # Try invoking Lambda asynchronously
    try:
        response = lambda_client.invoke(
            FunctionName=WORKER_LAMBDA_NAME,
            InvocationType="Event",
            Payload=json.dumps(payload),
        )
        logger.info(f"Worker Lambda invoked successfully: {WORKER_LAMBDA_NAME}")
    except Exception as e:
        logger.error(f"Failed to invoke worker Lambda, attempting to use Fargate: {str(e)}")
        
        # Fallback to Fargate if Lambda invocation fails
        try:
            response = ecs_client.run_task(
                cluster='<your_cluster_name>',
                launchType='FARGATE',
                taskDefinition='<your_task_definition>',
                count=1,
                networkConfiguration={
                    'awsvpcConfiguration': {
                        'subnets': ['<subnet_id>'],
                        'assignPublicIp': 'ENABLED'
                    }
                },
                overrides={
                    'containerOverrides': [
                        {
                            'name': '<your_container_name>',
                            'command': ["python", "lambda_worker.py"],
                            'environment': [
                                {
                                    'name': 'QUERY_PAYLOAD',
                                    'value': json.dumps(payload)
                                }
                            ]
                        }
                    ]
                }
            )
            logger.info("Fargate container started as a fallback for Lambda failure.")
        except Exception as fargate_error:
            logger.error(f"Failed to invoke Fargate task as fallback: {str(fargate_error)}")
            raise HTTPException(status_code=500, detail="Failed to invoke worker Lambda or Fargate task")


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
