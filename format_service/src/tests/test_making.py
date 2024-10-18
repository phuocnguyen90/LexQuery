# tests/test_masking.py

import unittest
from utils.validation import mask_api_key
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestMaskApiKey(unittest.TestCase):
    def test_standard_key(self):
        self.assertEqual(mask_api_key("12345678abcd"), "***abcd")
    
    def test_short_key(self):
        self.assertEqual(mask_api_key("abcd"), "***")
    
    def test_empty_key(self):
        self.assertEqual(mask_api_key(""), "***")
    
    def test_non_string_key(self):
        self.assertEqual(mask_api_key(1234), "***")

if __name__ == '__main__':
    unittest.main()
