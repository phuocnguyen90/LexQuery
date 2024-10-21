import unittest
from unittest.mock import patch, MagicMock
import boto3
import json
import os
from botocore.exceptions import ClientError
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import Logger 
from shared_libs.config.config_loader import ConfigLoader
from pathlib import Path
config=ConfigLoader()
print(f"DEVELOPMENT_MODE: {os.getenv('DEVELOPMENT_MODE')}")
print(f"LOG_TABLE_NAME: {os.getenv('LOG_TABLE_NAME')}")
print(f"Using AWS_REGION: {os.getenv('AWS_REGION')}")

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOCAL_LOG_FILE = LOG_DIR / "session_logs.json"


class TestLogger(unittest.TestCase):
    @patch("boto3.resource")
    def test_log_event_to_dynamodb(self, mock_boto_resource):
        # Mock DynamoDB Table
        mock_dynamodb = MagicMock()
        mock_table = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb

        # Simulate successful put_item call
        mock_table.put_item.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}

        # Create Logger instance with DynamoDB enabled
        logger = Logger.get_logger(module_name=__name__)
        logger.log_table = mock_table  # Assigning the mocked table to logger

        # Log an event
        event_message = "This is a test log event."
        logger.info(event_message)

        # Verify that put_item was called with correct parameters
        self.assertTrue(mock_table.put_item.called)
        args, kwargs = mock_table.put_item.call_args
        log_entry = kwargs["Item"]

        # Check if the log entry contains the expected values
        self.assertEqual(log_entry["message"], event_message)
        self.assertEqual(log_entry["event_type"], "INFO")
        self.assertIn("log_id", log_entry)
        self.assertIn("timestamp", log_entry)

    @patch("boto3.resource")
    def test_log_event_fallback_to_local(self, mock_boto_resource):
        # Mock DynamoDB to raise a ResourceNotFoundException
        mock_dynamodb = MagicMock()
        mock_table = MagicMock()
        mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ResourceNotFoundException", "Message": "Table not found"}},
            "PutItem"
        )
        mock_dynamodb.Table.return_value = mock_table
        mock_boto_resource.return_value = mock_dynamodb

        # Create Logger instance with DynamoDB enabled
        logger = Logger(name="TestLogger")
        logger.log_table = mock_table  # Assigning the mocked table to logger

        # Log an event
        event_message = "This is a test log event for local fallback."
        logger.info(event_message)

        # Verify that put_item was called and failed
        self.assertTrue(mock_table.put_item.called)

        # Verify that the log was saved locally
        with open(LOCAL_LOG_FILE, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            self.assertTrue(any(entry["message"] == event_message for entry in log_data))

    @classmethod
    def tearDownClass(cls):
        # Clean up the local log file after tests
        if LOCAL_LOG_FILE.exists():
            LOCAL_LOG_FILE.unlink()

if __name__ == "__main__":
    unittest.main()
