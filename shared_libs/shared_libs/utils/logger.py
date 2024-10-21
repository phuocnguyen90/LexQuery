import os
import logging
import boto3
import time
import uuid
import json
from botocore.exceptions import ClientError
from pathlib import Path
from dotenv import load_dotenv

class Logger:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton pattern to ensure only one instance of the logger
        if not cls._instance:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        # Load environment variables from .env file
        base_dir = Path(__file__).resolve().parent.parent
        dotenv_path = base_dir / "config/.env"
        if dotenv_path.exists():
            load_dotenv(dotenv_path)
        
        # Environment configuration
        self.LOG_TABLE_NAME = os.getenv("LOG_TABLE_NAME")
        self.AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
        self.S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "legal-rag-qa")
        self.DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"

        # Create logger
        self.logger = logging.getLogger("ProjectLogger")

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Set logger level based on environment
        log_level = logging.DEBUG if self.DEVELOPMENT_MODE else logging.INFO
        self.logger.setLevel(log_level)

        # Define log file path
        self.LOG_DIR = Path("logs")
        self.LOG_DIR.mkdir(exist_ok=True)
        self.LOCAL_LOG_FILE = self.LOG_DIR / "project_logs.json"

        # Create formatter
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler for local logs
        file_handler = logging.FileHandler(self.LOG_DIR / "project_logs.log")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        self.logger.debug("Logger initialized successfully.")

        # Initialize AWS clients
        if not self.DEVELOPMENT_MODE:
            try:
                self.dynamodb = boto3.resource("dynamodb", region_name=self.AWS_REGION)
                self.s3 = boto3.client("s3", region_name=self.AWS_REGION)
                self.log_table = self.dynamodb.Table(self.LOG_TABLE_NAME)
                self.logger.debug(f"DynamoDB table '{self.LOG_TABLE_NAME}' and S3 bucket '{self.S3_BUCKET_NAME}' initialized successfully.")
            except ClientError as e:
                self.logger.error(f"Failed to initialize AWS services: {e.response['Error']['Message']}")
                self.dynamodb = None
                self.s3 = None
                self.log_table = None
        else:
            self.logger.debug("Running in development mode. AWS services are not initialized.")

    def get_logger(self):
        return self.logger

    def log_event(self, event_type, message, details=None):
        log_entry = {
            "cache_key": str(uuid.uuid4()),
            "log_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": int(time.time()),
            "message": message,
            "details": details if details else {}
        }

        # Try to log to DynamoDB if available
        if self.log_table:
            try:
                self.logger.debug(f"Attempting to log event to DynamoDB: {log_entry}")
                self.log_table.put_item(Item=log_entry)
                self.logger.debug(f"Log entry successfully created in DynamoDB: {log_entry['log_id']}")
                return
            except ClientError as e:
                self.logger.error(f"Failed to log event to DynamoDB: {e.response['Error']['Message']}")

        # Fall back to local logging
        self._log_to_local(log_entry)

    def _log_to_local(self, log_entry):
        """Log locally to the file system."""
        try:
            self.logger.debug(f"Attempting to log event locally: {log_entry}")
            if self.LOCAL_LOG_FILE.exists():
                with self.LOCAL_LOG_FILE.open('r', encoding='utf-8') as f:
                    log_data = json.load(f)
            else:
                log_data = []

            log_data.append(log_entry)

            with self.LOCAL_LOG_FILE.open('w', encoding='utf-8') as f:
                json.dump(log_data, f, indent=2)

            self.logger.debug(f"Log entry saved locally: {log_entry['log_id']}")
        except Exception as e:
            self.logger.error(f"Failed to log event locally: {str(e)}")

    def save_logs_to_s3(self):
        """Upload local logs to S3 if they exist and AWS services are initialized."""
        if self.s3 and self.LOCAL_LOG_FILE.exists():
            try:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                s3_key = f"logs/session_logs_{timestamp}.json"
                with self.LOCAL_LOG_FILE.open('rb') as f:
                    self.s3.put_object(Bucket=self.S3_BUCKET_NAME, Key=s3_key, Body=f)
                self.logger.debug(f"Local logs saved to S3 bucket: {self.S3_BUCKET_NAME} with key: {s3_key}")

                # Optionally, delete the local log file after uploading
                self.LOCAL_LOG_FILE.unlink()
            except ClientError as e:
                self.logger.error(f"Failed to save logs to S3: {e.response['Error']['Message']}")
            except Exception as e:
                self.logger.error(f"Unexpected error while saving logs to S3: {str(e)}")

    # Convenience methods for different log levels
    def info(self, message, details=None):
        self.logger.debug(message)
        self.log_event(event_type="INFO", message=message, details=details)

    def error(self, message, details=None):
        self.logger.error(message)
        self.log_event(event_type="ERROR", message=message, details=details)

    def debug(self, message, details=None):
        if self.DEVELOPMENT_MODE:
            self.logger.debug(message)
        self.log_event(event_type="DEBUG", message=message, details=details)

    def warning(self, message, details=None):
        self.logger.warning(message)
        self.log_event(event_type="WARNING", message=message, details=details)

# Example usage in another module
if __name__ == "__main__":
    # Initialize logger instance
    logger_instance = Logger().get_logger()

    logger_instance.info("This is an info message")
    logger_instance.debug("This is a debug message")
    logger_instance.warning("This is a warning message")
    logger_instance.error("This is an error message")
