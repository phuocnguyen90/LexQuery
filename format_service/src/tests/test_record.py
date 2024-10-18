# tests/test_record.py

import unittest
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.load_config import load_config
from utils.record import Record

class TestParseRecord(unittest.TestCase):
    def setUp(self):
        self.valid_tagged_text = """
        <id=1>
        <title>Sample Title</title>
        <published_date>2024-09-22</published_date>
        <categories><Category1><Category2></categories>
        <content>
        Sample content here.
        </content>
        </id=1>
        """
        self.invalid_tagged_text_missing_title = """
        <id=2>
        <published_date>2024-10-01</published_date>
        <categories><CategoryA></categories>
        <content>
        Another sample content.
        </content>
        </id=2>
        """
        self.invalid_tagged_text_malformed = """
        <id=3>
        <title>Malformed Title<title>
        <published_date>2024-10-15</published_date>
        <categories><CategoryX></categories>
        <content>
        Malformed content here.
        </content>
        </id=3>
        """

    def test_parse_record_as_record_valid(self):
        record = Record.parse_record(self.valid_tagged_text, return_type="record")
        self.assertIsInstance(record, Record)
        self.assertEqual(record.record_id, 1)
        self.assertEqual(record.title, "Sample Title")
        self.assertEqual(record.published_date, "2024-09-22")
        self.assertListEqual(record.categories, ["Category1", "Category2"])
        self.assertEqual(record.content, "Sample content here.")

    def test_parse_record_as_dict_valid(self):
        record_dict = Record.parse_record(self.valid_tagged_text, return_type="dict")
        self.assertIsInstance(record_dict, dict)
        self.assertEqual(record_dict['record_id'], 1)
        self.assertEqual(record_dict['title'], "Sample Title")
        self.assertEqual(record_dict['published_date'], "2024-09-22")
        self.assertListEqual(record_dict['categories'], ["Category1", "Category2"])
        self.assertEqual(record_dict['content'], "Sample content here.")

    def test_parse_record_as_json_valid(self):
        record_json = Record.parse_record(self.valid_tagged_text, return_type="json")
        self.assertIsInstance(record_json, str)
        record = json.loads(record_json)
        self.assertEqual(record['record_id'], 1)
        self.assertEqual(record['title'], "Sample Title")
        self.assertEqual(record['published_date'], "2024-09-22")
        self.assertListEqual(record['categories'], ["Category1", "Category2"])
        self.assertEqual(record['content'], "Sample content here.")

    def test_parse_record_invalid_missing_field(self):
        record = Record.parse_record(self.invalid_tagged_text_missing_title, return_type="record")
        self.assertIsNone(record)

    def test_parse_record_invalid_malformed(self):
        record = Record.parse_record(self.invalid_tagged_text_malformed, return_type="record")
        self.assertIsNone(record)

    def test_parse_record_invalid_return_type(self):
        record = Record.parse_record(self.valid_tagged_text, return_type="invalid_type")
        self.assertIsNone(record)

if __name__ == '__main__':
    unittest.main()