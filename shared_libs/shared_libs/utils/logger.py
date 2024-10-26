import os
import logging
from pathlib import Path
from dotenv import load_dotenv

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
        self.DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "True").lower() == "true"

        # Create logger
        self.logger = logging.getLogger("ProjectLogger")

        if self.logger.hasHandlers():
            self.logger.handlers.clear()

        # Set logger level based on environment
        log_level = logging.DEBUG if self.DEVELOPMENT_MODE else logging.INFO
        self.logger.setLevel(log_level)

        # Create formatter with module name
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s (Source Module: %(source_module)s)"
        )

        # Console handler with UTF-8 encoding
        console_handler = logging.StreamHandler(stream=sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)

        # Set encoding for console handler (Python 3.9+)
        if hasattr(console_handler.stream, 'reconfigure'):
            console_handler.stream.reconfigure(encoding='utf-8')

        self.logger.addHandler(console_handler)

        # File handler for local logs with UTF-8 encoding (only in development)
        if self.DEVELOPMENT_MODE:
            self.LOG_DIR = Path("logs")
            self.LOG_DIR.mkdir(exist_ok=True)
            self.LOCAL_LOG_FILE = self.LOG_DIR / "project_logs.log"
            file_handler = logging.FileHandler(self.LOCAL_LOG_FILE, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Add the filter before any logging occurs
        self.logger.addFilter(self._add_default_module_name)

        self.logger.info("Logger initialized successfully.")

    def _add_default_module_name(self, record):
        # Add a default value for 'source_module' if it does not exist in the record
        if 'source_module' not in record.__dict__:
            record.source_module = 'UnknownModule'
        return True

    @classmethod
    def get_logger(cls, module_name=None):
        # Get the instance of Logger if not already created
        if cls._instance is None:
            cls._instance = Logger()

        # Return a LoggerAdapter with the source_module information
        return logging.LoggerAdapter(
            cls._instance.logger,
            {'source_module': module_name if module_name else 'UnknownModule'}
        )