# tests/test_parsing.py

import unittest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file_handler import parse_record
from utils.record import Record


class TestParsing(unittest.TestCase):
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

    def test_parse_record_valid(self):
        record = parse_record(self.valid_tagged_text)
        self.assertIsNotNone(record)
        self.assertEqual(record['id'], 1)
        self.assertEqual(record['title'], "Sample Title")
        self.assertEqual(record['published_date'], "2024-09-22")
        self.assertListEqual(record['categories'], ["Category1", "Category2"])
        self.assertEqual(record['content'], "Sample content here.")

    def test_parse_record_invalid_missing_title(self):
        record = parse_record(self.invalid_tagged_text_missing_title)
        self.assertIsNone(record)

    def test_record_from_tagged_text_valid(self):
        record_obj = Record.from_tagged_text(self.valid_tagged_text)
        self.assertIsNotNone(record_obj)
        self.assertEqual(record_obj.id, 1)
        self.assertEqual(record_obj.title, "Sample Title")
        self.assertEqual(record_obj.published_date, "2024-09-22")
        self.assertListEqual(record_obj.categories, ["Category1", "Category2"])
        self.assertEqual(record_obj.content, "Sample content here.")

    def test_record_from_tagged_text_invalid(self):
        record_obj = Record.from_tagged_text(self.invalid_tagged_text_missing_title)
        self.assertIsNone(record_obj)

if __name__ == '__main__':
    unittest.main()
