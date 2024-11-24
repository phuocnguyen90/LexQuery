# tests/test_rag_service.py
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from shared_libs.utils.deprecated.query_cache import ProcessedMessageCache
from shared_libs.config.config_loader import ConfigLoader
from shared_libs.utils.deprecated.get_provider import get_groq_provider

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import the FastAPI app and other components
from src.handlers.api_handler import app
from rag_service.src.services.deprecated.query_rag_v1 import query_rag, QueryResponse
from src.models.query_model import QueryModel

# Initialize TestClient for API
client = TestClient(app)

# Mock Data for Testing
mock_query_text = "What are the legal implications of contract breaches?"
mock_query_response = "The legal implications of contract breaches can include compensatory damages, restitution, rescission, etc."

# Test API Endpoints
def test_index():
    """Test the root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

@patch("src.handlers.api_handler.QueryModel.get_item")
def test_get_query_endpoint(mock_get_item):
    """Test the /get_query endpoint"""
    mock_get_item.return_value = {"query_id": "12345", "query_text": mock_query_text}
    response = client.get("/get_query", params={"query_id": "12345"})
    assert response.status_code == 200
    assert response.json()["query_text"] == mock_query_text

@patch("src.handlers.api_handler.query_rag")
@patch("src.handlers.api_handler.QueryModel.put_item")
def test_submit_query_endpoint(mock_put_item, mock_query_rag):
    """Test the /submit_query endpoint"""
    mock_query_rag.return_value = QueryResponse(
        query_text=mock_query_text,
        response_text=mock_query_response,
        sources=["source1", "source2"]
    )
    response = client.post("/submit_query", json={"query_text": mock_query_text})
    assert response.status_code == 200
    assert response.json()["answer_text"] == mock_query_response
    assert response.json()["sources"] == ["source1", "source2"]

@patch("src.rag.query_rag.search_qdrant")
@patch("shared_libs.utils.provider_utils.get_groq_provider")
def test_query_rag(mock_get_groq_provider, mock_search_qdrant):
    """Unit test for query_rag functionality"""
    mock_search_qdrant.return_value = [
        {"record_id": "QA_1", "source": "source1", "content": "Some legal content here"},
        {"record_id": "QA_2", "source": "source2", "content": "Another legal content here"}
    ]

    # Mocking the provider's send_single_message method
    mock_provider = MagicMock()
    mock_provider.send_single_message.return_value = mock_query_response
    mock_get_groq_provider.return_value = mock_provider

    # Call the function to test
    response = query_rag(mock_query_text)
    assert response.query_text == mock_query_text
    assert response.response_text == mock_query_response
    assert len(response.sources) == 2

# Test Cache Functionality
def test_cache():
    """Test caching functionality"""
    cache = ProcessedMessageCache()
    # Cache response
    cache.cache_response(mock_query_text, mock_query_response)
    # Retrieve response
    cached_response = QueryModel.get_item_by_cache_key(mock_query_text)
    assert cached_response == mock_query_response

    # Clear the cache if in development mode
    if os.getenv("DEVELOPMENT_MODE", "True") == "True":
        cache.clear_cache()
        cached_response = QueryModel.get_item_by_cache_key(mock_query_text)
        assert cached_response is None

# Test Config Loading
def test_load_config():
    """Test the config loader to ensure it loads properly"""
    config = ConfigLoader().get_config()
    assert "groq" in config
    assert config.get("groq", {}).get("api_key") is not None

# Mocking Redis for Local Cache Testing (Optional)
@patch("redis.Redis.get")
@patch("redis.Redis.set")
def test_redis_cache(mock_set, mock_get):
    """Test Redis cache in development mode"""
    mock_get.return_value = mock_query_response.encode("utf-8")
    cache = ProcessedMessageCache()
    # Test get_cached_response
    response = QueryModel.get_item_by_cache_key(mock_query_text)
    assert response == mock_query_response
    # Test cache_response
    cache.cache_response(mock_query_text, mock_query_response)
    mock_set.assert_called_once_with(mock_query_text, mock_query_response, ex=3600)

# Test LLM Provider (Optional)
@patch("shared_libs.providers.groq_provider.GroqProvider.send_single_message")
def test_llm_provider(mock_send_single_message):
    """Test the LLM provider (Groq)"""
    mock_send_single_message.return_value = mock_query_response
    provider = get_groq_provider()
    response = provider.send_single_message(mock_query_text)
    assert response == mock_query_response
