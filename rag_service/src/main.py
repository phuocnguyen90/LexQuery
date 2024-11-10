# src/main.py

import os
import json
import uuid
import asyncio
from typing import List, Dict, Optional

import boto3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from mangum import Mangum

# Import from shared_libs
from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.utils.logger import Logger

# Import internal model and services
from models.query_model import QueryModel
from services.query_rag import query_rag

# Initialize configuration and logger
config = AppConfigLoader()
logger = Logger.get_logger(module_name=__name__)

# Environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
WORKER_LAMBDA_NAME = os.getenv("WORKER_LAMBDA_NAME", "RagWorker")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Initialize synchronous boto3 clients
lambda_client = boto3.client(
    'lambda',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)
ecs_client = boto3.client(
    'ecs',
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
handler = Mangum(app)

# Data models
class SubmitQueryRequest(BaseModel):
    query_text: str
    conversation_history: Optional[List[Dict[str, str]]] = None  # Optional field
    llm_provider_name: Optional[str] = None

class SubmitQueryResponse(BaseModel):
    query_id: str
    response_text: Optional[str] = None
    sources: Optional[List[str]] = None
    timestamp: Optional[str] = None
    message: Optional[str] = None

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
        }
    logger.warning(f"Query not found for ID: {query_id}")
    raise HTTPException(status_code=404, detail="Query not found")

@app.post("/submit_query")
async def submit_query_endpoint(request: SubmitQueryRequest):
    """
    Endpoint to submit a user query for processing synchronously.

    :param request: SubmitQueryRequest containing the query_text and optional conversation_history.
    :return: SubmitQueryResponse with query_id and processed response.
    """
    try:
        query_text = request.query_text
        llm_provider_name = request.llm_provider_name
        query_id = str(uuid.uuid4())  # Generate unique query_id
        conversation_history = request.conversation_history or []
        logger.info(f"Received submit query request: '{query_text}', assigned query_id: {query_id}")

        # Step 1: Check Cache for Existing Response
        existing_query = await QueryModel.get_item(query_id)
        if existing_query and existing_query.is_complete:
            logger.info(f"Cache hit for query_id: {query_id}")
            return SubmitQueryResponse(
                query_id=existing_query.query_id,
                response_text=existing_query.answer_text,
                sources=existing_query.sources,
                timestamp=existing_query.timestamp
            )

        # Step 2: Process the Query Synchronously
        logger.info(f"Processing query_id: {query_id} synchronously")
        query_item = QueryModel(query_id=query_id, query_text=query_text)
        response = await query_rag(
            query_item=query_item,
            conversation_history=conversation_history,
            llm_provider_name=llm_provider_name
        )

        # Step 3: Update and Save the QueryModel with the Response
        query_item.answer_text = response.response_text
        query_item.sources = response.sources
        query_item.is_complete = True
        query_item.timestamp = response.timestamp
        await query_item.put_item()
        logger.info(f"Query processed synchronously for query_id: {query_id}")

        # Step 4: Return the Response to the Client
        return {
            "query_id": query_id,
            "response_text": response.response_text,
            "sources": response.sources,
            "timestamp": response.timestamp
        }

    except Exception as exc:
        logger.error(f"Failed to handle submit_query endpoint: {str(exc)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Remove SQS-related functions as they are no longer needed
# Removed invoke_worker and related SQS logic

# For local development and testing
if __name__ == "__main__":
    import uvicorn
    port = 8000
    logger.info(f"Running the FastAPI server on port {port}.")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
