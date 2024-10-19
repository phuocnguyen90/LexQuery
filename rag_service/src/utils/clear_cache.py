import boto3
from shared_libs.utils.query_cache import ProcessedMessageCache
cache=ProcessedMessageCache()
cache.clear_cache()