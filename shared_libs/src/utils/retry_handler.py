# utils/retry_handler.py

import time
import logging
from functools import wraps
# logging.getLogger(__name__)
def retry(max_attempts=2, delay=2, backoff=2):
    """
    Decorator to retry a function in case of exceptions.
    :param max_attempts: Maximum number of attempts.
    :param delay: Initial delay between attempts.
    :param backoff: Multiplier for delay on each retry.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logging.warning(f"Attempt {attempts} failed with error: {e}")
                    if attempts < max_attempts:
                        logging.info(f"Retrying after {current_delay} seconds...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logging.error(f"All {max_attempts} attempts failed.")
                        raise
        return wrapper
    return decorator
