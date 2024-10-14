# tests/test_query_rag.py

import unittest
from unittest.mock import MagicMock
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag_app.query_rag import query_rag, QueryResponse

class TestQueryRag(unittest.TestCase):
    def setUp(self):
        # Mock GroqProvider
        self.groq_provider = MagicMock()
        self.groq_provider.send_message.return_value = "Theo quy định trong [Mã tài liệu: QA_750F0D91], ..."

        # Mock search_qdrant
        self.mock_docs = [
            {"record_id": "QA_750F0D91", "source": "Nguồn 1", "content": "Nội dung 1"},
            {"record_id": "QA_12345678", "source": "Nguồn 2", "content": "Nội dung 2"}
        ]
        from rag_app.search_qdrant import search_qdrant
        search_qdrant = MagicMock(return_value=self.mock_docs)

    def test_query_rag_success(self):
        from rag_app.query_rag import query_rag
        query_text = "Cha có bắt buộc để lại di sản thừa kế cho con của vợ trước?"
        response = query_rag(query_text, self.groq_provider)
        self.assertIsInstance(response, QueryResponse)
        self.assertEqual(response.query_text, query_text)
        self.assertEqual(response.sources, ["QA_750F0D91", "QA_12345678"])
        self.groq_provider.send_message.assert_called_once()

    def test_query_rag_no_results(self):
        from rag_app.query_rag import query_rag
        from rag_app.search_qdrant import search_qdrant
        search_qdrant.return_value = []
        query_text = "Non-existent query?"
        response = query_rag(query_text, self.groq_provider)
        self.assertEqual(response.response_text, "Không tìm thấy thông tin liên quan.")
        self.assertEqual(response.sources, [])
        self.groq_provider.send_message.assert_not_called()

    def test_validate_citation(self):
        from rag_app.query_rag import validate_citation
        valid_response = "Theo quy định trong [Mã tài liệu: QA_750F0D91], ..."
        invalid_response = "This is a response without citation."
        self.assertTrue(validate_citation(valid_response))
        self.assertFalse(validate_citation(invalid_response))

if __name__ == '__main__':
    unittest.main()
