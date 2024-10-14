import logging

def setup_logger():
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger("RAGApp")
    logger.info("Logger is configured")
