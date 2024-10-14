# utils/rate_limiter.py

import time
import logging

# logging.getLogger(__name__)
class RateLimiter:
    def __init__(self, max_calls, period):
        """
        Initialize the rate limiter.
        :param max_calls: Maximum number of calls allowed within the period.
        :param period: Time period in seconds.
        """
        self.max_calls = max_calls
        self.period = period
        self.call_times = []

    def wait(self):
        """
        Wait if the rate limit has been reached.
        """
        current_time = time.time()
        # Remove calls that are outside the current period
        self.call_times = [t for t in self.call_times if t > current_time - self.period]
        if len(self.call_times) >= self.max_calls:
            wait_time = self.period - (current_time - self.call_times[0])
            logging.info(f"Rate limit reached. Waiting for {wait_time} seconds.")
            time.sleep(wait_time)
        self.call_times.append(time.time())
