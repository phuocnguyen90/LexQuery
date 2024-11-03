# rag_service\src\handlers\work_handler.py
import os
from shared_libs.config.config_loader import AppConfigLoader
from shared_libs.utils.logger import Logger
from shared_libs.llm_providers import ProviderFactory
import sys
import json
import asyncio
import boto3
from botocore.exceptions import ClientError
from functools import partial
from hashlib import md5
# Add parent directory to the sys.path to access shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.query_model import QueryModel
from services.query_rag import query_rag

# Initialize the logger
logger = Logger().get_logger(module_name=__name__)

# Load configuration and LLM provider
app_config_loader = AppConfigLoader()
config = app_config_loader.config
provider_name = config.get('llm', {}).get('provider', 'groq')
llm_settings = config.get('llm', {}).get(provider_name, {})
llm_provider = ProviderFactory.get_provider(provider_name, llm_settings)

# Worker configuration
POLL_INTERVAL = 10  # seconds
MAX_MESSAGES = 10 
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")

# Initialize boto3 clients
sqs_client = boto3.client('sqs', region_name=AWS_REGION)

async def handler(event, context):
    for record in event['Records']:
        try:
            payload = json.loads(record['body'])
            query_id = payload.get('query_id')
            if not query_id:
                logger.error("No query_id found in payload.")
                continue  # Skip processing if no query_id

            conversation_history = payload.get('conversation_history', [])
            llm_provider_name = payload.get('llm_provider')
            if llm_provider_name:
                provider_config = config.get('llm', {}).get(llm_provider_name, {})
                if provider_config:
                    provider = ProviderFactory.get_provider(llm_provider_name, provider_config)
                    logger.info(f"Using specified LLM provider: {llm_provider_name}")
                else:
                    logger.error(f"Specified LLM provider '{llm_provider_name}' not found in configuration. Using default provider.")
                    provider = llm_provider  # Use default provider
            else:
                provider = llm_provider

            query_item = await QueryModel.get_item(query_id)
            if not query_item:
                logger.error(f"No query found in database for query_id: {query_id}")
                continue

            # Invoke RAG processing with cache handling
            response = await query_rag(query_item, provider=provider, conversation_history=conversation_history)

            # Update the query item with the response
            query_item.answer_text = response.response_text
            query_item.sources = response.sources
            query_item.is_complete = True
            query_item.timestamp = response.timestamp 

            # Save the updated query_item to DynamoDB or cache
            await query_item.update_item(query_id,query_item)
            
            logger.info(f"Successfully processed query_id: {query_id}")

            # Delete the message from the queue after successful processing
            await delete_message(record['ReceiptHandle'])
            logger.info(f"Deleted message from SQS for query_id: {query_id}")

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Optionally, handle retries or dead-letter queue


async def process_message(message):
    """
    Process a single SQS message.
    """
    try:
        # Deserialize message
        body = json.loads(message['Body'])
        llm_provider_name = body.get('llm_provider')
        
        if llm_provider_name:            
            # Get provider configuration from config
            provider_config = config.get('llm', {}).get(llm_provider_name, {})
            if provider_config:
                provider = ProviderFactory.get_provider(llm_provider_name, provider_config)
                logger.info(f"Using specified LLM provider: {llm_provider_name}")
            else:
                logger.error(f"Specified LLM provider '{llm_provider_name}' not found in configuration. Using default provider.")
                provider = llm_provider  # Use default provider
        else:
            provider = llm_provider  # Use default provider
        query_id = body.get('query_id')
        if not query_id:
            logger.error("No query_id found in message body.")
            # Delete the message to prevent it from being retried indefinitely
            await delete_message(message['ReceiptHandle'])
            return

        logger.info(f"Received message for query_id: {query_id}")
        query_text = body.get('query_text')
        if not query_text:
            logger.error(f"No query_text found in message body for query_id: {query_id}")
            # Delete the message to prevent it from being retried indefinitely
            await delete_message(message['ReceiptHandle'])
            return

        conversation_history = body.get('conversation_history', [])

        logger.info(f"Processing query: {query_text}")

        # Create or retrieve the query from your data store (e.g., DynamoDB)
        query_item = QueryModel(
            query_id=query_id,
            query_text=query_text,
            conversation_history=conversation_history
        )

        # Perform RAG to generate response
        response = await query_rag(
            query_item,
            conversation_history=conversation_history,
            provider=provider
        )

        # Update the query item with the response
        query_item.answer_text = response.response_text
        query_item.sources = response.sources
        query_item.is_complete = True
        query_item.timestamp = response.timestamp  
               
        # Set the response into the cache using query_text as the key
        await query_item.update_item(query_id,query_item)
        logger.info(f"Query processed and saved for query_id: {query_id}")


        # Delete the message from the queue after successful processing
        await delete_message(message['ReceiptHandle'])
        logger.info(f"Successfully processed and deleted message for query_id: {query_id}")

    except Exception as e:
        logger.error(f"Error processing message for query_id {query_id}: {str(e)}")
        # Depending on requirements, you can decide to delete the message or leave it for retry
        # For now, we'll leave it to be retried


async def delete_message(receipt_handle):
    """
    Delete a message from the SQS queue.
    """
    try:
        loop = asyncio.get_event_loop()
        delete_partial = partial(
            sqs_client.delete_message,
            QueueUrl=SQS_QUEUE_URL,
            ReceiptHandle=receipt_handle
        )
        await loop.run_in_executor(
            None,
            delete_partial
        )
        logger.debug("Message deleted from SQS.")
    except Exception as e:
        logger.error(f"Failed to delete message from SQS: {str(e)}")

async def poll_queue():
    """
    Continuously poll the SQS queue for new messages.
    """
    while True:
        try:
            # Receive messages with long polling
            receive_partial = partial(
                sqs_client.receive_message,
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=MAX_MESSAGES,
                WaitTimeSeconds=20  # Enable long polling
            )
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                receive_partial
            )

            messages = response.get('Messages', [])
            if not messages:
                logger.debug("No messages received.")
            else:
                logger.info(f"Received {len(messages)} messages.")

                # Process each message concurrently
                tasks = [process_message(message) for message in messages]
                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error polling SQS queue: {str(e)}")

        # Wait before next poll to avoid tight loop
        await asyncio.sleep(POLL_INTERVAL)

# For local testing

def main():
    """
    Entry point for the worker handler.
    """
    logger.info("Worker handler started. Polling SQS queue...")
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(poll_queue())
    except KeyboardInterrupt:
        logger.info("Worker handler stopped manually.")
    finally:
        loop.close()

if __name__ == "__main__":
    main()