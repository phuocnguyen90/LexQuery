import os
import boto3
import time
import uuid
import json
from botocore.exceptions import ClientError
import logging
from pathlib import Path

# Environment Settings
LOG_TABLE_NAME = os.getenv("LOG_TABLE_NAME", "LogTable")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", True)  # Use "production" for production environment

# Initialize AWS Services in Production
if DEVELOPMENT_MODE==False:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    s3 = boto3.client("s3", region_name=AWS_REGION)
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-log-bucket")

# Local log file setup for Development Environment
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOCAL_LOG_FILE = LOG_DIR / "session_logs.json"

# Configure local logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Logger:
    @staticmethod
    def log_event(event_type, message, details=None):
        """Log an event to DynamoDB or local log file based on the environment."""
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": int(time.time()),
            "message": message,
            "details": details if details else {}
        }

        if DEVELOPMENT_MODE == False:
            # Log to DynamoDB
            try:
                table = dynamodb.Table(LOG_TABLE_NAME)
                table.put_item(Item=log_entry)
                logger.info(f"Log entry created in DynamoDB: {log_entry['log_id']}")
            except ClientError as e:
                logger.error(f"Failed to log event to DynamoDB: {e.response['Error']['Message']}")
        else:
            # Log locally
            try:
                # Load existing local logs if available
                if LOCAL_LOG_FILE.exists():
                    with LOCAL_LOG_FILE.open('r', encoding='utf-8') as f:
                        log_data = json.load(f)
                else:
                    log_data = []

                # Append the new log entry
                log_data.append(log_entry)

                # Write updated log data back to the local file
                with LOCAL_LOG_FILE.open('w', encoding='utf-8') as f:
                    json.dump(log_data, f, indent=2)

                logger.info(f"Log entry saved locally: {log_entry['log_id']}")
            except Exception as e:
                logger.error(f"Failed to log event locally: {str(e)}")

    @staticmethod
    def save_logs_to_s3():
        """Save local logs to S3 at the end of the session if in production."""
        if DEVELOPMENT_MODE == False:
            try:
                if LOCAL_LOG_FILE.exists():
                    with LOCAL_LOG_FILE.open('rb') as f:
                        s3.put_object(Bucket=S3_BUCKET_NAME, Key=f"logs/{LOCAL_LOG_FILE.name}", Body=f)
                    logger.info(f"Local logs saved to S3 bucket: {S3_BUCKET_NAME}")

                    # Optionally, delete the local log file after uploading
                    LOCAL_LOG_FILE.unlink()
                else:
                    logger.info("No local log file found to save to S3.")
            except ClientError as e:
                logger.error(f"Failed to save logs to S3: {e.response['Error']['Message']}")
        else:
            logger.info("Skipping S3 upload since the environment is not production.")
