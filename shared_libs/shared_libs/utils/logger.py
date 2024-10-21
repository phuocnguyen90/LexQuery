import os
import logging
import boto3
import time
import uuid
import json
from botocore.exceptions import ClientError
from pathlib import Path
from dotenv import load_dotenv
import watchtower
import re
import sys

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

        # Create formatter with module name
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s (Source Module: %(source_module)s)")

        # Console handler with UTF-8 encoding
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        # Set encoding for console handler (Python 3.9+)
        if hasattr(console_handler.stream, 'reconfigure'):
            console_handler.stream.reconfigure(encoding='utf-8')

        self.logger.addHandler(console_handler)

        # File handler for local logs with UTF-8 encoding
        file_handler = logging.FileHandler(self.LOG_DIR / "project_logs.log", encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # CloudWatch Logs handler
        if not self.DEVELOPMENT_MODE:
            try:
                cloudwatch_client = boto3.client('logs', region_name=self.AWS_REGION)

                # Check if the log group exists, otherwise create it
                log_group_name = "rag-legal-qa"
                try:
                    cloudwatch_client.describe_log_groups(logGroupNamePrefix=log_group_name)
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        cloudwatch_client.create_log_group(logGroupName=log_group_name)

                # Create a CloudWatch Logs Handler
                sanitized_log_stream_name = re.sub(r"[:*/]", "_", f"{Path(__file__).stem}/{self.logger.name}/{uuid.uuid4()}")
                cloudwatch_handler = watchtower.CloudWatchLogHandler(
                    log_group=log_group_name,
                    log_stream_name=sanitized_log_stream_name,
                    use_queues=True,
                    create_log_group=True,
                    boto3_client=cloudwatch_client
                )
                cloudwatch_handler.setLevel(log_level)
                cloudwatch_handler.setFormatter(formatter)
                self.logger.addHandler(cloudwatch_handler)
                self.logger.info("CloudWatch Logs handler initialized successfully.")
            except ClientError as e:
                self.logger.error(f"Failed to initialize CloudWatch Logs handler: {e.response['Error']['Message']}")

        self.logger.info("Logger initialized successfully.")

    @classmethod
    def get_logger(cls, module_name=None):
        # Get the instance of Logger if not already created
        if cls._instance is None:
            cls._instance = Logger()

        # Return a LoggerAdapter with the source_module information
        return logging.LoggerAdapter(cls._instance.logger, {'source_module': module_name if module_name else 'UnknownModule'})

    # Convenience methods for different log levels (Optional if you prefer direct usage)
    def log_event(self, event_type, message, details=None, module_name=None):
        log_entry = {
            "log_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": int(time.time()),
            "message": message,
            "details": details if details else {}
        }
        # Log the event with the source_module name
        self.get_logger(module_name).info(json.dumps(log_entry, ensure_ascii=False))

    def info(self, message, details=None, module_name=None):
        logger = self.get_logger(module_name)
        logger.info(message)
        self.log_event(event_type="INFO", message=message, details=details, module_name=module_name)

    def error(self, message, details=None, module_name=None):
        logger = self.get_logger(module_name)
        logger.error(message)
        self.log_event(event_type="ERROR", message=message, details=details, module_name=module_name)

    def debug(self, message, details=None, module_name=None):
        logger = self.get_logger(module_name)
        if self.DEVELOPMENT_MODE:
            logger.debug(message)
        self.log_event(event_type="DEBUG", message=message, details=details, module_name=module_name)

    def warning(self, message, details=None, module_name=None):
        logger = self.get_logger(module_name)
        logger.warning(message)
        self.log_event(event_type="WARNING", message=message, details=details, module_name=module_name)

# Example usage in another module
if __name__ == "__main__":
    # Initialize logger instance by module name
    logger_instance = Logger.get_logger(module_name=__name__)

    logger_instance.info("This is an info message from main module with Unicode: thử nghiệm")
    logger_instance.debug("This is a debug message from main module with Unicode: 🚀")
    logger_instance.warning("This is a warning message from main module with Unicode: こんにちは")
    logger_instance.error("This is an error message from main module with Unicode: Привет")
