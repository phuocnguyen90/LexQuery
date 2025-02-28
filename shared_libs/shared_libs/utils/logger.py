import os
import logging
from pathlib import Path
from dotenv import load_dotenv
import sys

class ProjectLoggerAdapter(logging.LoggerAdapter):
    def raw(self, msg, *args, **kwargs):
        """
        Log a raw response message intended for testers.
        This message will be directed to the dedicated raw response log file.
        """
        extra = self.extra.copy() if self.extra else {}
        extra.update(kwargs.get('extra', {}))
        extra['log_type'] = "raw"
        kwargs['extra'] = extra
        self.log(logging.INFO, msg, *args, **kwargs)

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
        self.DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() == "true"
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
            # Standard formatter for normal logs (developer-oriented)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s (Source Module: %(source_module)s)"
            )

            # Console handler with UTF-8 encoding
            console_handler = logging.StreamHandler(stream=sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            if hasattr(console_handler.stream, 'reconfigure'):
                console_handler.stream.reconfigure(encoding='utf-8')
            self.logger.addHandler(console_handler)

            # Create a dedicated log folder within the project (e.g., "logs")
            self.LOG_DIR = base_dir / "logs"
            self.LOG_DIR.mkdir(parents=True, exist_ok=True)

            # File handler for local logs (developer logs)
            self.LOCAL_LOG_FILE = self.LOG_DIR / "project_logs.log"
            file_handler = logging.FileHandler(self.LOCAL_LOG_FILE, encoding='utf-8')
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            self.logger.info(f"Developer log file set to: {self.LOCAL_LOG_FILE.absolute()}")

            # Create a dedicated file handler for raw responses (tester logs)
            self.RAW_LOG_FILE = self.LOG_DIR / "raw_response.log"
            raw_handler = logging.FileHandler(self.RAW_LOG_FILE, encoding='utf-8')
            raw_handler.setLevel(logging.INFO)  # Adjust level as needed
            raw_formatter = logging.Formatter("%(asctime)s: %(message)s")
            raw_handler.setFormatter(raw_formatter)
            # Only allow log records that have log_type == "raw"
            raw_handler.addFilter(lambda record: hasattr(record, 'log_type') and record.log_type == "raw")
            self.logger.addHandler(raw_handler)
            self.logger.info(f"Tester log file set to: {self.RAW_LOG_FILE.absolute()}")

            # Add filter to add default source_module if not provided
            self.logger.addFilter(self._add_default_module_name)
            self.logger.info("Logger initialized successfully.")

    def _add_default_module_name(self, record):
        if 'source_module' not in record.__dict__:
            record.source_module = 'UnknownModule'
        return True

    @classmethod
    def get_logger(cls, module_name=None):
        if cls._instance is None:
            cls._instance = Logger()

        adapter = ProjectLoggerAdapter(
            cls._instance.logger,
            {'source_module': module_name if module_name else 'UnknownModule'}
        )
        if not hasattr(adapter, 'raw'):
            def raw(msg, *args, **kwargs):
                extra = adapter.extra.copy() if adapter.extra else {}
                extra.update(kwargs.get('extra', {}))
                extra['log_type'] = "raw"
                kwargs['extra'] = extra
                adapter.log(logging.INFO, msg, *args, **kwargs)
            adapter.raw = raw
        return adapter
