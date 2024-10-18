# tests/test_enrichment_processor.py

import pytest
import pandas as pd
from unittest.mock import patch
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enrichment_processor import EnrichmentProcessor
from utils.load_config import load_config
from tests.sample_text import sample_text

# Sample enriched data that the mocked LLM should return
mock_enriched_data = {
    'Main Topic': 'Regulation of Financial Institutions',
    'Applicability': 'Applies to all financial entities operating within the jurisdiction.',
    'Generated Title': 'Regulation of Financial Institutions',
    'Assigned Categories': ['Financial Law', 'Regulatory Compliance']
}

# Function to simulate LLM response
def mock_format_text(raw_text, mode="enrichment", provider=None):
    """
    Mock function to replace the LLMProvider's format_text method.
    """
    if mode == "enrichment":
        return f"""Main Topic: {mock_enriched_data['Main Topic']}
Applicability: {mock_enriched_data['Applicability']}
Generated Title: {mock_enriched_data['Generated Title']}
Suggested Categories: {', '.join(mock_enriched_data['Assigned Categories'])}"""
    return ""

def test_enrichment_processor(mocker):
    """
    Unit test for the EnrichmentProcessor using a mocked LLMProvider.
    """
    # Load the configuration
    config = load_config('config/config.yaml', 'config/.env')

    # Create a sample documents dataframe
    documents_data = [{
        'Category': 'Law',
        'Document ID': '1',
        'Document Name': 'General Provisions',
        'Hierarchy Level': 1,
        'Document Path': 'path/to/document1.txt',
        'Parent Document ID': None
    }]
    documents_df = pd.DataFrame(documents_data)

    # Initialize the EnrichmentProcessor
    enrichment_processor = EnrichmentProcessor(config=config, documents_df=documents_df)

    # Mock the read_file_content function to return the sample_text
    mocker.patch('utils.file_handler.read_file_content', return_value=sample_text)

    # Mock the LLMFormatter's format_text method
    with patch('utils.llm_client.LLMFormatter.format_text', side_effect=mock_format_text):
        enriched_df = enrichment_processor.process_documents()

    # Assertions to verify the enriched data
    assert len(enriched_df) == 1, "There should be exactly one enriched record."
    enriched_record = enriched_df.iloc[0]

    assert enriched_record['Category'] == 'Law'
    assert enriched_record['Document ID'] == '1'
    assert enriched_record['Hierarchy Level'] == 1
    assert enriched_record['Document Path'] == 'path/to/document1.txt'
    assert enriched_record['Parent Document ID'] is None
    assert enriched_record['Chunk ID'] == '1.1'
    assert enriched_record['Chunk Text'].strip() != "", "Chunk text should not be empty."
    assert enriched_record['Main Topic'] == mock_enriched_data['Main Topic']
    assert enriched_record['Applicability'] == mock_enriched_data['Applicability']
    assert enriched_record['Generated Title'] == mock_enriched_data['Generated Title']
    assert enriched_record['Assigned Categories'] == mock_enriched_data['Assigned Categories']
    assert enriched_record['Validation Status'] == True, "Record should pass validation."

    print("All assertions passed for the enrichment processor unit test.")

def test_enrichment_processor_empty_chunk(mocker):
    """
    Unit test to verify that the EnrichmentProcessor handles empty document chunks gracefully.
    """
    # Load the configuration
    config = load_config('config/config.yaml', 'config/.env')

    # Create a sample documents dataframe with an empty document
    documents_data = [{
        'Category': 'Law',
        'Document ID': '2',
        'Document Name': 'Empty Document',
        'Hierarchy Level': 1,
        'Document Path': 'path/to/document2.txt',
        'Parent Document ID': None
    }]
    documents_df = pd.DataFrame(documents_data)

    # Initialize the EnrichmentProcessor
    enrichment_processor = EnrichmentProcessor(config=config, documents_df=documents_df)

    # Mock the read_file_content function to return an empty string
    mocker.patch('utils.file_handler.read_file_content', return_value="")

    # Mock the LLMFormatter's format_text method
    with patch('utils.llm_client.LLMFormatter.format_text', side_effect=mock_format_text):
        enriched_df = enrichment_processor.process_documents()

    # Assertions to verify that no records are enriched
    assert len(enriched_df) == 0, "No enriched records should be present for empty document chunks."

    print("All assertions passed for empty document chunk unit test.")
