# shared_libs/utils/logger.py

import os
import boto3
import time
import uuid
import json
import logging
from botocore.exceptions import ClientError
from pathlib import Path

# Environment Settings
LOG_TABLE_NAME = os.getenv("LOG_TABLE_NAME", "LogTable")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"

# AWS Services for Production
if not DEVELOPMENT_MODE:
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    s3 = boto3.client("s3", region_name=AWS_REGION)
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "your-log-bucket")

# Local log file setup for Development Environment
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOCAL_LOG_FILE = LOG_DIR / "session_logs.json"

# Configure base logging
logging.basicConfig(level=logging.DEBUG if DEVELOPMENT_MODE else logging.INFO)
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class Logger:
    def __init__(self, name: str):
        self.logger = self.get_logger(name)
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """
        Get a logger instance with handlers configured for the environment.
        
        :param name: Name of the logger, typically the module's __name__.
        :return: Configured logger instance.
        """
        logger = logging.getLogger(name)

        if not logger.handlers:
            # Prevent adding multiple handlers to the same logger
            if DEVELOPMENT_MODE:
                # Console Handler for Development
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(log_formatter)
                console_handler.setLevel(logging.DEBUG)

                # File Handler for Development
                file_handler = logging.FileHandler(LOG_DIR / "app_debug.log")
                file_handler.setFormatter(log_formatter)
                file_handler.setLevel(logging.DEBUG)

                # Add handlers to the logger
                logger.setLevel(logging.DEBUG)
                logger.addHandler(console_handler)
                logger.addHandler(file_handler)
            else:
                # Console Handler for Production
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(log_formatter)
                console_handler.setLevel(logging.INFO)

                # Add handlers to the logger
                logger.setLevel(logging.INFO)
                logger.addHandler(console_handler)

        return logger

    def log_event(self, event_type, message, details=None):
        """Log an event to DynamoDB or local log file based on the environment."""
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": int(time.time()),
            "message": message,
            "details": details if details else {}
        }

        if not DEVELOPMENT_MODE:
            # Log to DynamoDB in production
            try:
                table = dynamodb.Table(LOG_TABLE_NAME)
                table.put_item(Item=log_entry)
                self.logger.info(f"Log entry created in DynamoDB: {log_entry['log_id']}")
            except ClientError as e:
                self.logger.error(f"Failed to log event to DynamoDB: {e.response['Error']['Message']}")
        else:
            # Log locally in development mode
            try:
                if LOCAL_LOG_FILE.exists():
                    with LOCAL_LOG_FILE.open('r', encoding='utf-8') as f:
                        log_data = json.load(f)
                else:
                    log_data = []

                log_data.append(log_entry)

                with LOCAL_LOG_FILE.open('w', encoding='utf-8') as f:
                    json.dump(log_data, f, indent=2)

                self.logger.info(f"Log entry saved locally: {log_entry['log_id']}")
            except Exception as e:
                self.logger.error(f"Failed to log event locally: {str(e)}")

    @staticmethod
    def save_logs_to_s3():
        """Save local logs to S3 at the end of the session if in production."""
        if not DEVELOPMENT_MODE:
            try:
                if LOCAL_LOG_FILE.exists():
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    s3_key = f"logs/session_logs_{timestamp}.json"
                    with LOCAL_LOG_FILE.open('rb') as f:
                        s3.put_object(Bucket=S3_BUCKET_NAME, Key=s3_key, Body=f)
                    logging.getLogger(__name__).info(f"Local logs saved to S3 bucket: {S3_BUCKET_NAME} with key: {s3_key}")

                    # Optionally, delete the local log file after uploading
                    LOCAL_LOG_FILE.unlink()
                else:
                    logging.getLogger(__name__).info("No local log file found to save to S3.")
            except ClientError as e:
                logging.getLogger(__name__).error(f"Failed to save logs to S3: {e.response['Error']['Message']}")
        else:
            logging.getLogger(__name__).info("Skipping S3 upload since the environment is not production.")

    def log_info(self, message, details=None):
        """Helper method to log an info event."""
        self.log_event(event_type="INFO", message=message, details=details)

    def log_error(self, message, details=None):
        """Helper method to log an error event."""
        self.log_event(event_type="ERROR", message=message, details=details)

    def log_debug(self, message, details=None):
        """Helper method to log a debug event."""
        self.log_event(event_type="DEBUG", message=message, details=details)

    def log_warning(self, message, details=None):
        """Helper method to log a warning event."""
        self.log_event(event_type="WARNING", message=message, details=details)