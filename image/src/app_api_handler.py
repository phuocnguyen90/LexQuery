# src/app_api_handler.py

import os
import uvicorn
import boto3
import json

from fastapi import FastAPI, HTTPException
from mangum import Mangum
from pydantic import BaseModel
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from query_model import QueryModel
from rag.query_rag import query_rag  
from utils.provider_utils import get_groq_provider
from utils.load_config import ConfigLoader

WORKER_LAMBDA_NAME = os.environ.get("WORKER_LAMBDA_NAME", None)

# Load the configuration globally so that it persists across invocations if the Lambda container is reused
config = ConfigLoader().get_config()

# Initialize the GroqProvider globally for reusability
groq_provider = get_groq_provider()

# Initialize FastAPI application
app = FastAPI()

# Entry point for AWS Lambda using Mangum
deployment_handler = Mangum(app)

class SubmitQueryRequest(BaseModel):
    query_text: str

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
    else:
        # Handle the RAG processing directly (useful for local development)
        query_response = query_rag(request.query_text, groq_provider)  # Use the globally defined groq_provider
        new_query.answer_text = query_response.response_text
        new_query.sources = query_response.sources
        new_query.is_complete = True
        new_query.put_item()

    return new_query

def invoke_worker(query: QueryModel):
    # Initialize the Lambda client
    lambda_client = boto3.client("lambda")

    # Get the QueryModel as a dictionary
    payload = query.dict()

    # Invoke the worker Lambda function asynchronously
    response = lambda_client.invoke(
        FunctionName=WORKER_LAMBDA_NAME,
        InvocationType="Event",
        Payload=json.dumps(payload),
    )

    print(f"✅ Worker Lambda invoked: {response}")

if __name__ == "__main__":
    # For local development testing
    port = 8000
    print(f"Running the FastAPI server on port {port}.")
    uvicorn.run("app_api_handler:app", host="0.0.0.0", port=port)
