class ProcessedMessageCache:
    def __init__(self, table_name="ProcessedMessages"):
        self.table = dynamodb.Table(table_name)

    def get_cached_response(self, query_text):
        try:
            response = self.table.get_item(Key={"query_text": query_text})
            if "Item" in response:
                return response["Item"].get("response_text")
            return None
        except ClientError as e:
            print(f"Error fetching cached response: {e.response['Error']['Message']}")
            return None

    def cache_response(self, query_text, response_text):
        try:
            self.table.put_item(
                Item={
                    "query_text": query_text,
                    "response_text": response_text,
                    "timestamp": int(time.time())
                }
            )
            print(f"Response cached for query: {query_text}")
        except ClientError as e:
            print(f"Error caching response: {e.response['Error']['Message']}")
