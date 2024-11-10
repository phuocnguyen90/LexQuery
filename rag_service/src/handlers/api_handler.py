# src/handlers/api_handler.py

import os
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
from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.utils.logger import Logger

import sys
# Add parent directory to the sys.path to access shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import internal model
from models.query_model import QueryModel
from services.query_rag import query_rag  # Ensure this is available for local processing

config = AppConfigLoader()
# Initialize logger
logger = Logger.get_logger(module_name=__name__)

# Environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", "RagWorker")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() in ["true", "1", "yes"]
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Initialize boto3 clients
lambda_client = boto3.client(
    'lambda',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
sqs_client = boto3.client(
    'sqs',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

# Initialize FastAPI application
app = FastAPI()

# Entry point for AWS Lambda using Mangum
handler = Mangum(app) if not DEVELOPMENT_MODE else None

# Data models
class SubmitQueryRequest(BaseModel):
    query_text: str
    conversation_history: Optional[List[Dict[str, str]]] = None  # Optional field
    llm_provider: Optional[str] = None

# Processor Interface
class Processor:
    async def process_query(self, query: QueryModel, conversation_history: List[Dict[str, str]], llm_provider_name: Optional[str] = None) -> Dict:
        raise NotImplementedError("Processor must implement process_query method.")

# Production Processor using Worker Lambda
class LambdaWorkerProcessor(Processor):
    def __init__(self, lambda_client, worker_lambda_name, sqs_client=None, sqs_queue_url=None):
        self.lambda_client = lambda_client
        self.worker_lambda_name = worker_lambda_name
        self.sqs_client = sqs_client
        self.sqs_queue_url = sqs_queue_url

    async def process_query(self, query: QueryModel, conversation_history: List[Dict[str, str]], llm_provider_name: Optional[str] = None) -> Dict:
        try:
            payload = query.dict()
            payload["conversation_history"] = conversation_history
            if llm_provider_name:
                payload["llm_provider"] = llm_provider_name
            message_body = json.dumps(payload)
            logger.debug(f"Invoking worker lambda synchronously with payload: {message_body}")

            # Invoke the worker lambda synchronously
            response = self.lambda_client.invoke(
                FunctionName=self.worker_lambda_name,
                InvocationType="RequestResponse",  # Synchronous invocation
                Payload=message_body.encode('utf-8'),
            )
            # Read and decode the response payload
            response_payload = json.loads(response['Payload'].read().decode('utf-8'))
            logger.debug(f"Worker lambda response: {response_payload}")
            return response_payload
        except Exception as e:
            logger.error(f"Failed to invoke worker lambda: {str(e)}")
            # Optionally, enqueue to SQS if synchronous invocation fails
            if self.sqs_client and self.sqs_queue_url:
                try:
                    await self.enqueue_to_sqs(query, conversation_history, llm_provider_name)
                    return {
                        "query_id": query.query_id,
                        "message": "Your query has been received and is being processed asynchronously."
                    }
                except Exception as sqs_error:
                    logger.error(f"Failed to enqueue to SQS after Lambda invocation failure: {str(sqs_error)}")
                    raise HTTPException(status_code=500, detail="Failed to process query.")
            else:
                raise HTTPException(status_code=500, detail="Failed to process query.")

    async def enqueue_to_sqs(self, query: QueryModel, conversation_history: List[Dict[str, str]], llm_provider_name: Optional[str] = None):
        payload = query.dict()
        payload["conversation_history"] = conversation_history
        if llm_provider_name:
            payload["llm_provider"] = llm_provider_name
        message_body = json.dumps(payload)
        logger.debug(f"Sending message to SQS: {message_body}")

        loop = asyncio.get_event_loop()
        send_message_partial = partial(
            self.sqs_client.send_message,
            QueueUrl=self.sqs_queue_url,
            MessageBody=message_body
        )
        response = await loop.run_in_executor(
            None,
            send_message_partial
        )
        logger.debug(f"Message sent to SQS: {response.get('MessageId')}")

# Development Processor (Local Processing)
class LocalProcessor(Processor):
    def __init__(self):
        pass  # Initialize any local resources if needed

    async def process_query(self, query: QueryModel, conversation_history: List[Dict[str, str]], llm_provider_name: Optional[str] = None) -> Dict:
        try:
            logger.info(f"Processing query locally for query_id: {query.query_id}")
            response = await query_rag(query, conversation_history=conversation_history, llm_provider_name=llm_provider_name)
            # Update the query item with the response
            query.answer_text = response.response_text
            query.sources = response.sources
            query.is_complete = True
            query.timestamp = response.timestamp 

            # Save the updated query_item to DynamoDB or cache
            await query.update_item(query.query_id, query)
            logger.info(f"Successfully processed query_id: {query.query_id} locally.")

            return {
                "query_id": query.query_id,
                "response_text": query.answer_text,
                "sources": query.sources,
                "timestamp": query.timestamp
            }
        except Exception as e:
            logger.error(f"Failed to process query locally: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to process query locally.")

# Initialize Processor based on environment
if DEVELOPMENT_MODE:
    processor = LocalProcessor()
    logger.info("Running in Development Mode: Using LocalProcessor.")
else:
    if not WORKER_LAMBDA_NAME:
        logger.error("WORKER_LAMBDA_NAME environment variable is not set.")
        raise Exception("WORKER_LAMBDA_NAME environment variable is required in production.")
    processor = LambdaWorkerProcessor(lambda_client, WORKER_LAMBDA_NAME, sqs_client_sync, SQS_QUEUE_URL)
    logger.info("Running in Production Mode: Using LambdaWorkerProcessor.")

# API Endpoints
@app.get("/")
def index():
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
            "timestamp": query.timestamp
        }
    logger.warning(f"Query not found for ID: {query_id}")
    raise HTTPException(status_code=404, detail="Query not found")

@app.post("/submit_query")
async def submit_query_endpoint(request: SubmitQueryRequest):
    """
    Endpoint to submit a user query for processing.

    In Production:
        - Invokes the worker Lambda to process the query.
        - Waits for the worker to complete and returns the result.

    In Development:
        - Processes the query locally and returns the result directly.

    :param request: SubmitQueryRequest containing the query_text and optional conversation_history.
    :return: JSON response with query_id and processed result or status message.
    """
    try:
        query_text = request.query_text
        llm_provider_name = request.llm_provider
        query_id = str(uuid.uuid4())  # Generate unique query_id
        conversation_history = request.conversation_history or []
        logger.info(f"Received submit query request: {query_text}, assigned query_id: {query_id}")

        # Step 1: Check Cache for Existing Response
        existing_query = await QueryModel.get_item(query_id)
        if existing_query and existing_query.is_complete:
            logger.info(f"Cache hit for query_id: {query_id}")
            return {
                "query_id": existing_query.query_id,
                "response_text": existing_query.answer_text,
                "sources": existing_query.sources,
                "timestamp": existing_query.timestamp
            }

        # Step 2: Create new query and save it
        new_query = QueryModel(query_id=query_id, query_text=query_text)
        await new_query.put_item()
        logger.debug(f"New query object created: {new_query.query_id}")

        # Step 3: Process the query using the appropriate processor
        response_payload = await processor.process_query(new_query, conversation_history, llm_provider_name)

        # Step 4: Return the response to the client
        return response_payload

    except Exception as exc:
        logger.error(f"Failed to handle submit_query endpoint: {str(exc)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Local Development Function to Test API Endpoints

if __name__ == "__main__":
    if DEVELOPMENT_MODE:
        import uvicorn
        port = 8000
        logger.info(f"Running the FastAPI server on port {port} in Development Mode.")
        uvicorn.run("handlers.api_handler:app", host="0.0.0.0", port=port)
    else:
        # Lambda handler is already defined above
        pass

# Optional: Remove or comment out the local testing endpoint as it's no longer needed
# since the `/submit_query` endpoint handles both production and development modes.
