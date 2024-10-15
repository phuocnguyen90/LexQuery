import os
import redis
import json

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))

# Initialize Redis connection
cache_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

class Cache:
    @staticmethod
    def set(key, value, expiry=3600):
        """Set a value in Redis with an optional expiry time."""
        cache_client.set(key, json.dumps(value), ex=expiry)

    @staticmethod
    def get(key):
        """Get a value from Redis."""
        value = cache_client.get(key)
        if value:
            return json.loads(value)
        return None
