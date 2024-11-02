# src/handlers/api_handler.py

import os
import uvicorn
import boto3
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mangum import Mangum
import uuid
import asyncio
from functools import partial
from typing import List, Dict, Optional

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

config = ConfigLoader()
# Initialize logger
logger = Logger.get_logger(module_name=__name__)

# Environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", "RagWorker")

# Initialize synchronous boto3 clients
lambda_client = boto3.client("lambda", region_name=AWS_REGION)
ecs_client = boto3.client("ecs", region_name=AWS_REGION)
sqs_client_sync = boto3.client('sqs', region_name=AWS_REGION)

# Load the LLM provider (abstracted utility function handles fallbacks)
llm_provider = load_llm_provider()

# Initialize FastAPI application
app = FastAPI()

# Entry point for AWS Lambda using Mangum
deployment_handler = Mangum(app)

# Data models
class SubmitQueryRequest(BaseModel):
    query_text: str
    conversation_history: Optional[List[Dict[str, str]]] = None  # Optional field

# API Endpoints
@app.get("/")
async def index():
    return {"Hello": "World"}

@app.get("/get_query")
async def get_query_endpoint(query_id: str):

    logger.debug(f"Fetching query with ID: {query_id}")
    query = await QueryModel.get_item(query_id)
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
    """
    Endpoint to submit a user query for processing.

    If a worker is available, it processes the query immediately.
    Otherwise, it enqueues the query in SQS and triggers a worker to process it asynchronously.

    :param request: SubmitQueryRequest containing the query_text and optional conversation_history.
    :return: JSON response with query_id and status message.
    """
    try:
        query_text = request.query_text
        query_id = str(uuid.uuid4())  # Generate unique query_id
        conversation_history = request.conversation_history or []
        logger.info(f"Received submit query request: {query_text}, assigned query_id: {query_id}")

        # Step 1: Check Cache for Existing Response
        existing_query = await QueryModel.get(query_id)
        if existing_query and existing_query.is_complete:
            logger.info(f"Cache hit for query_id: {query_id}")
            return {
                "query_id": existing_query.query_id,
                "response_text": existing_query.answer_text,
                "sources": existing_query.sources,
                "timestamp": existing_query.timestamp
    }
        # Step 2: Process the Query
        if WORKER_LAMBDA_NAME:
            # Worker is available, enqueue the query for asynchronous processing
            new_query = QueryModel(query_id=query_id, query_text=query_text)
            await new_query.put_item()
            logger.debug(f"New query object created: {new_query.query_id}")
        
            # Enqueue the query for processing
            await invoke_worker(new_query, conversation_history)

            # Step 3: Return the query_id to the client
            return {
                "query_id": query_id,
                "message": "Your query has been received and is being processed."
            }
        else:
            # No worker available, process synchronously
            logger.info("No worker available. Processing query synchronously.")
            response = await query_rag(
                query_item=QueryModel(query_id=query_id, query_text=query_text),
                conversation_history=conversation_history
            )
            # Store the response in cache or database
            await Cache.set(query_id, response.dict())  # Assuming Cache.set uses query_id as key
            logger.info(f"Query processed synchronously for query_id: {query_id}")

            return {
                "query_id": query_id,
                "response_text": response.response_text,
                "sources": response.sources,
                "timestamp": response.timestamp
            }

        

    except Exception as exc:
        logger.error(f"Failed to handle submit_query endpoint: {str(exc)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def invoke_worker(query: QueryModel, conversation_history: List[Dict[str, str]]):
    """Enqueue the query for processing by sending a message to SQS."""
    try:
        # Convert QueryModel to dict and then to JSON
        payload = query.dict()
        payload["conversation_history"] = conversation_history
        message_body = json.dumps(payload)
        logger.debug(f"Sending message to SQS: {message_body}")

        # Since boto3 is synchronous, run the send_message in executor
        loop = asyncio.get_event_loop()
        send_message_partial = partial(
            sqs_client_sync.send_message,
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=message_body
        )
        response = await loop.run_in_executor(
            None,
            send_message_partial
        )
        logger.debug(f"Message sent to SQS: {response.get('MessageId')}")
        # Invoke another Lambda function asynchronously
        response = lambda_client.invoke(
            FunctionName=WORKER_LAMBDA_NAME,
            InvocationType="Event",
            Payload=message_body.encode('utf-8'),
        )
    except Exception as e:
        logger.error(f"Failed to send message to SQS: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to enqueue query for processing")

# Local Development Function to Test API Endpoints
if __name__ == "__main__":
    # For local development testing
    port = 8000
    logger.info(f"Running the FastAPI server on port {port}.")
    uvicorn.run("handlers.api_handler:app", host="0.0.0.0", port=port)

# Add a local testing endpoint for convenience
@app.post("/local_test_submit_query")
async def local_test_submit_query(request: SubmitQueryRequest):
    """
    This endpoint is for local testing only. It allows you to submit a query
    and get an immediate response without relying on the worker Lambda.
    """
    query_text = request.query_text
    logger.info("Local testing endpoint called")

    # Generate a query_id
    query_id = str(uuid.uuid4())
    new_query = QueryModel(query_id=query_id, query_text=query_text)

    # Process the query using RAG (local)
    query_response = await query_rag(new_query, llm_provider)
    response_data = {
        "query_id": query_id,  # Include query_id
        "query_text": query_text,
        "answer_text": query_response.response_text,
        "sources": query_response.sources,
        "is_complete": True,
    }

    # Store response in cache
    await Cache.set(query_text, response_data, expiry=1800)  # Ensure expiry is set

    logger.info("Query processed and cached during local testing")

    return response_data
