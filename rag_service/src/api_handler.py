# src/handlers/api_handler.py

import os
import boto3
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from mangum import Mangum
import uuid
import asyncio
import time
from functools import partial
from typing import List, Dict, Optional
from hashlib import md5
from services.intention_detector import IntentionDetector

# Import from shared_libs
from shared_libs.config.app_config import AppConfigLoader
from shared_libs.utils.logger import Logger

import sys
# Add parent directory to sys.path to access shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import internal model and query function
from models.query_model import QueryModel
from services.query_rag import query_rag  

# Load configuration and initialize logger
config = AppConfigLoader()
logger = Logger.get_logger(module_name=__name__)

# Environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", "RagWorker")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() in ["true", "1", "yes"]
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

if DEVELOPMENT_MODE:
    endpoint_url = os.getenv("AWS_ENDPOINT_URL", "http://localstack:4566")
else:
    endpoint_url = None

# Initialize boto3 clients
lambda_client = boto3.client(
    'lambda',
    region_name=AWS_REGION,
    endpoint_url=endpoint_url
)
sqs_client = boto3.client(
    'sqs',
    region_name=AWS_REGION,
    endpoint_url=endpoint_url
)

# Initialize IntentionDetector
intention_detector = IntentionDetector()

# Initialize FastAPI application
app = FastAPI()

# Allow origins as needed
allowed_origins = [
    "https://phuocmaster.blog",  
    "https://www.yourwebsite.com",
    "http://localhost",
    "http://127.0.0.1",
    # Add other domains or subdomains if necessary
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Entry point for AWS Lambda using Mangum
handler = Mangum(app)

# Data models
class SubmitQueryRequest(BaseModel):
    query_text: str
    conversation_history: Optional[List[Dict[str, str]]] = None  # Optional field
    llm_provider: Optional[str] = None

# Processor Interface
class Processor:
    async def process_query(self, query: QueryModel, conversation_history: List[Dict[str, str]], 
                            llm_provider_name: Optional[str] = None) -> Dict:
        raise NotImplementedError("Processor must implement process_query method.")

# Production Processor using Worker Lambda
import logging

class LambdaWorkerProcessor(Processor):
    def __init__(self, lambda_client, worker_lambda_name, sqs_client=None, sqs_queue_url=None):
        self.lambda_client = lambda_client
        self.worker_lambda_name = worker_lambda_name
        self.sqs_client = sqs_client
        self.sqs_queue_url = sqs_queue_url
        self.logger = logging.getLogger(__name__)

    async def process_query(self, query: 'QueryModel', conversation_history: List[Dict[str, str]], 
                              llm_provider_name: Optional[str] = None) -> Dict:
        try:
            payload = query.dict()
            payload["conversation_history"] = conversation_history
            if llm_provider_name:
                payload["llm_provider"] = llm_provider_name
            message_body = json.dumps(payload)
            self.logger.debug(f"Invoking worker lambda synchronously with payload: {message_body}")

            response = self.lambda_client.invoke(
                FunctionName=self.worker_lambda_name,
                InvocationType="RequestResponse",
                Payload=message_body.encode('utf-8'),
            )

            # Read and decode the payload from the response
            payload_bytes = response['Payload'].read()
            payload_str = payload_bytes.decode('utf-8').strip()
            self.logger.debug(f"Raw worker payload: {payload_str}")

            # Check for a FunctionError flag in the response metadata
            if response.get('FunctionError'):
                self.logger.error(f"Worker lambda error: {payload_str}")
                raise Exception(f"Worker lambda returned an error: {payload_str}")

            try:
                response_payload = json.loads(payload_str)
            except json.JSONDecodeError as jde:
                self.logger.error(f"JSON decode error: {jde}; raw payload: {payload_str}")
                self.logger.info(f"Worker lambda parsed response payload: {response_payload}")
                raise Exception("Failed to parse JSON from worker lambda response.")

            

            # If the worker returned an error, raise an exception.
            if "error" in response_payload:
                error_msg = response_payload["error"]
                self.logger.error(f"Worker lambda returned error: {error_msg}")
                raise Exception(f"Worker lambda error: {error_msg}")

            query_response = response_payload.get("query_response")
            if not query_response:
                self.logger.error("Worker lambda did not return a valid query_response.")
                self.logger.info(f"Worker lambda response: {response_payload}")
                raise Exception("Worker lambda did not return a valid query_response.")

            # Build the final response payload as expected by the API.
            response_payload_final = {
                "query_id": query.query_id,
                "response_text": query_response.get("response_text"),
                "sources": query_response.get("sources"),
                "timestamp": query_response.get("timestamp")
            }

            self.logger.info(f"Final worker lambda response: {response_payload_final}")
            return response_payload_final

        except Exception as e:
            self.logger.error(f"Failed to invoke worker lambda synchronously: {str(e)}")
            # In production, do not fall back to SQS; simply raise an error.
            if DEVELOPMENT_MODE and self.sqs_client and self.sqs_queue_url:
                try:
                    await self.enqueue_to_sqs(query, conversation_history, llm_provider_name)
                    return {
                        "query_id": query.query_id,
                        "message": "Your query has been received and is being processed asynchronously."
                    }
                except Exception as sqs_error:
                    self.logger.error(f"Failed to enqueue to SQS after Lambda invocation failure: {str(sqs_error)}")
                    raise HTTPException(status_code=500, detail="Failed to process query.")
            else:
                raise HTTPException(status_code=500, detail="Failed to process query synchronously.")

    async def enqueue_to_sqs(self, query: 'QueryModel', conversation_history: List[Dict[str, str]], 
                               llm_provider_name: Optional[str] = None):
        payload = query.dict()
        payload["conversation_history"] = conversation_history
        if llm_provider_name:
            payload["llm_provider"] = llm_provider_name
        message_body = json.dumps(payload)
        self.logger.debug(f"Enqueuing message to SQS: {message_body}")

        loop = asyncio.get_event_loop()
        send_message_partial = partial(
            self.sqs_client.send_message,
            QueueUrl=self.sqs_queue_url,
            MessageBody=message_body
        )
        response = await loop.run_in_executor(None, send_message_partial)
        self.logger.debug(f"Message enqueued to SQS with MessageId: {response.get('MessageId')}")

# Development Processor (Local Processing)
class LocalProcessor(Processor):
    def __init__(self):
        pass  # Initialize any local resources if needed

    async def process_query(self, query: QueryModel, conversation_history: List[Dict[str, str]], 
                              llm_provider_name: Optional[str] = None) -> Dict:
        try:
            logger.info(f"Processing query locally for query_id: {query.query_id}")

            # Call the updated query_rag function
            rag_response = await query_rag(query, conversation_history=conversation_history, 
                                           llm_provider_name=llm_provider_name)

            # Extract query_response
            query_response = rag_response.get("query_response")
            if not query_response:
                raise ValueError("query_response is missing from RAG response.")

            # Update the QueryModel with results
            query.response_text = query_response.response_text
            query.sources = query_response.sources
            query.is_complete = True
            query.timestamp = query_response.timestamp

            # Save the updated query item
            await query.update_item(query.query_id, query)

            rag_response["query_response"] = query_response.dict()

            # Return the entire RAG response
            return rag_response

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
    processor = LambdaWorkerProcessor(lambda_client, WORKER_LAMBDA_NAME, sqs_client, SQS_QUEUE_URL)
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
            "response_text": query.response_text,
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
    Uses IntentionDetector to classify and handle the query.
    """
    try:
        query_text = request.query_text
        llm_provider_name = request.llm_provider
        cache_key = md5(query_text.encode('utf-8')).hexdigest()
        query_id = str(uuid.uuid4())  # Generate unique query_id
        conversation_history = request.conversation_history or []
        logger.info(f"Received submit query request: {query_text}, assigned query_id: {query_id}")

        # Intention detection using LLM
        intention, response_text = await intention_detector.detect_intention(query_text, conversation_history)
        logger.info(f"Intention detected: {intention}")

        if intention in ['irrelevant', 'history']:
            # Return response_text directly for irrelevant and history cases
            return {
                "query_id": query_id,
                "response_text": response_text,
                "sources": [],
                "timestamp": int(time.time())
            }

        # Check for a cache hit
        existing_query = await QueryModel.get_item_by_cache_key(cache_key)
        if existing_query and existing_query.is_complete:
            logger.info(f"Cache hit for query_id: {query_id}")
            return {
                "query_id": existing_query.query_id,
                "response_text": existing_query.response_text,
                "sources": existing_query.sources,
                "timestamp": existing_query.timestamp
            }

        # Create a new query object and store it
        new_query = QueryModel(query_id=query_id, query_text=query_text)
        await new_query.put_item()
        logger.debug(f"New query object created: {new_query.query_id}")

        # Process the query using the processor (which calls the worker lambda synchronously)
        rag_response = await processor.process_query(new_query, conversation_history, llm_provider_name)
        
        # At this point, rag_response is expected to contain a valid "query_response"
        
        if not rag_response:
            logger.error("Worker lambda did not return a valid rag_response.")
            logger.debug(f"Worker lambda response: {rag_response}")
            raise HTTPException(status_code=500, detail="Worker lambda did not return a valid rag_response.")
        

        response_payload = {
            "query_id": query_id,
            "response_text": rag_response.get("response_text"),
            "sources": rag_response.get("sources"),
            "timestamp": rag_response.get("timestamp")
        }
        # Optionally include development-only information.
        if DEVELOPMENT_MODE:
            if "retrieved_docs" in rag_response:
                response_payload["retrieved_docs"] = rag_response.get("retrieved_docs")
            if "debug_prompt" in rag_response:
                response_payload["debug_prompt"] = rag_response.get("debug_prompt")

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
        uvicorn.run("api_handler:app", host="0.0.0.0", port=port)
    else:
        # In production, the Lambda handler (provided by Mangum) is used.
        pass
