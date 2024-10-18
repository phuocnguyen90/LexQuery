# utils/logging_setup.py

import logging
import sys
import os

def setup_logging(log_file: str, level: str = "INFO"):
    """
    Configure logging to file and console.

    :param log_file: Path to the log file.
    :param level: Logging level as a string (e.g., "DEBUG", "INFO").
    """
    # Convert the level string to a numeric level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # Ensure the log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            print(f"Created log directory: {log_dir}")
        except Exception as e:
            print(f"Failed to create log directory {log_dir}: {e}")
            # If directory creation fails, fallback to console-only logging
            numeric_level = logging.INFO

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)

    # Remove all existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and configure FileHandler
    try:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Failed to set up FileHandler: {e}")
        # If file handler fails, proceed with console handler only

    # Create and configure StreamHandler for console output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    # Log the setup completion
    logger.info(f"Logging is set up with level {logging.getLevelName(numeric_level)}.")
