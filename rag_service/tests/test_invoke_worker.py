# tests/test_invoke_worker.py
import unittest
from unittest.mock import patch
from moto import mock_sqs
import boto3
from src.handlers.api_handler import invoke_worker, QueryModel
import os

class TestInvokeWorker(unittest.TestCase):
    @mock_sqs
    def test_invoke_worker(self):
        # Set up mock SQS
        sqs = boto3.client('sqs', region_name='us-east-1', endpoint_url='https://sqs.us-east-1.amazonaws.com/396608786775/legal-rag-qa')
        queue = sqs.create_queue(QueueName='legal-rag-qa-queue')
        queue_url = queue['QueueUrl']

        # Update environment variables
        with patch.dict(os.environ, {'SQS_QUEUE_URL': queue_url, 'DEVELOPMENT_MODE': 'True'}):
            # Create a sample QueryModel
            query = QueryModel(
                query_id='test-query-id',
                query_text='Test query for invoke_worker',
                response_text=None,
                sources=[],
                is_complete=False
            )

            # Invoke the worker
            invoke_worker(query)

            # Verify the message was sent to SQS
            messages = sqs.receive_message(QueueUrl=queue_url)
            self.assertIn('Messages', messages)
            self.assertEqual(len(messages['Messages']), 1)
            self.assertEqual(json.loads(messages['Messages'][0]['Body'])['query_id'], 'test-query-id')

if __name__ == '__main__':
    unittest.main()
