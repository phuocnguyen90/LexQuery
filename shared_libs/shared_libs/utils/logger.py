# shared_libs/utils/logger.py

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
        # DEVELOPMENT_MODE defaults to False if not found
        self.DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() == "true"
        # LOG_LEVEL is optional and overrides DEVELOPMENT_MODE's log level
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", None)

        # Determine the effective log level
        if self.LOG_LEVEL:
            try:
                log_level = getattr(logging, self.LOG_LEVEL.upper())
                if not isinstance(log_level, int):
                    raise ValueError
            except (AttributeError, ValueError):
                print(f"Invalid LOG_LEVEL '{self.LOG_LEVEL}' specified. Falling back to default levels.")
                log_level = logging.DEBUG if self.DEVELOPMENT_MODE else logging.INFO
        else:
            log_level = logging.DEBUG if self.DEVELOPMENT_MODE else logging.INFO

        # Create logger
        self.logger = logging.getLogger("ProjectLogger")
        self.logger.setLevel(log_level)

        # Prevent adding multiple handlers if logger is already configured
        if not self.logger.hasHandlers():
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
                # Update log directory to /tmp/local_data
                self.LOG_DIR = Path("/tmp/local_data")
                self.LOG_DIR.mkdir(parents=True, exist_ok=True)
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
