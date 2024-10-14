import boto3
import uuid
from ..models import SubmitQueryRequest

TABLE_NAME = 'your_table_name'
dynamodb = boto3.resource('dynamodb', endpoint_url='http://dynamodb:8000')

def save_query_item(query_text: str):
    table = dynamodb.Table(TABLE_NAME)
    query = {
        "query_id": str(uuid.uuid4()),
        "query_text": query_text,
        "is_complete": False
    }
    table.put_item(Item=query)
    return query

def get_query_item(query_id: str):
    table = dynamodb.Table(TABLE_NAME)
    response = table.get_item(Key={"query_id": query_id})
    return response.get("Item")
