# src/handlers/api_handler.py
import os
import uvicorn
import boto3
import aioboto3
from botocore.exceptions import ClientError
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mangum import Mangum
import uuid

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
logger = Logger.get_logger(module_name=__name__)

# Environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", "RagWorker")

lambda_client = boto3.client("lambda", region_name=AWS_REGION)
ecs_client = boto3.client("ecs", region_name=AWS_REGION)
sqs_client = boto3.client('sqs', region_name=AWS_REGION)

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
async def index():
    return {"Hello": "World"}

@app.get("/get_query")
async def get_query_endpoint(query_id: str):
    logger.debug(f"Fetching query with ID: {query_id}")
    query = QueryModel.get_item(query_id)
    if query:
        return {
            "query_id": query.query_id,
            "query_text": query.query_text,
            "answer_text": query.answer_text,
            "is_complete": query.is_complete,
            "sources": query.sources,
        }
    logger.warning(f"Query not found for ID: {query_id}")
    raise HTTPException(status_code=404, detail="Query not found")


@app.post("/submit_query")
async def submit_query_endpoint(request: SubmitQueryRequest):
    try:
        query_text = request.query_text
        query_id = str(uuid.uuid4())  # Generate unique query_id
        logger.info(f"Received submit query request: {query_text}, assigned query_id: {query_id}")

        # Step 1: Check Cache for Existing Response
        cached_response = await Cache.get(query_text)
        if cached_response:
            logger.info(f"Cache hit for query: {query_text}")
            return {"query_id": cached_response.get("query_id"), **cached_response}

        # Step 2: Process the Query
        new_query = QueryModel(query_id=query_id, query_text=query_text)
        await new_query.put_item()  

        # Enqueue the query for processing
        await invoke_worker(new_query)

        # Step 3: Return the query_id to the client
        return {
            "query_id": query_id,
            "message": "Your query has been received and is being processed."
        }

    except Exception as exc:
        logger.error(f"Failed to handle submit_query endpoint: {str(exc)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



async def invoke_worker(query: QueryModel):
    session = aioboto3.Session()
    async with session.client('sqs', region_name=AWS_REGION) as sqs_client:
            payload = query.dict()
            message_body = json.dumps(payload)
            try:
                response = await sqs_client.send_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MessageBody=message_body
                )
                logger.debug(f"Message sent to SQS: {response.get('MessageId')}")
            except Exception as e:
                logger.error(f"Failed to send message to SQS: {str(e)}")
                raise HTTPException(status_code=500, detail="Failed to enqueue query for processing")

# Local Development Function to Test API Endpoints
if __name__ == "__main__":
    # For local development testing
    port = 8000
    logger.info(f"Running the FastAPI server on port {port}.")
    uvicorn.run("handlers.api_handler:app", host="127.0.0.1", port=port)

# Add a local testing endpoint for convenience
@app.post("/local_test_submit_query")
async def local_test_submit_query(request: SubmitQueryRequest):
    """
    This endpoint is for local testing only. It allows you to submit a query
    and get an immediate response without relying on the worker Lambda.
    """
    query_text = request.query_text
    logger.info("Local testing endpoint called")

    # Check the cache for the query
    cache_key = Cache._generate_cache_key(query_text)
    logger.debug(f"Checking cache for key: {cache_key}")

    cached_response = await Cache.get(query_text)
    if cached_response:
        logger.info("Cache hit during local testing")
        return cached_response

    # Process the query using RAG (local)
    query_response = await query_rag(query_text, llm_provider)
    response_data = {
        "query_text": query_text,
        "response_text": query_response.response_text,
        "sources": query_response.sources,
    }

    # Store response in cache
    await Cache.set(query_text, response_data)
    logger.info("Query processed and cached during local testing")

    return response_data
