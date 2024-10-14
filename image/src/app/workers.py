import boto3
from ..rag.query_rag import query_rag

WORKER_LAMBDA_NAME = 'local_worker_lambda'

def invoke_worker_sync(query):
    if WORKER_LAMBDA_NAME == 'local_worker_lambda':
        return handle_rag_locally(query)
    else:
        lambda_client = boto3.client('lambda')
        payload = query.dict()
        lambda_client.invoke(
            FunctionName=WORKER_LAMBDA_NAME,
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        return {"status": "invoked"}

def handle_rag_locally(query):
    # Direct call to the RAG function
    response = query_rag(query.query_text)
    query.answer_text = response.response_text
    query.sources = response.sources
    query.is_complete = True
    return query
