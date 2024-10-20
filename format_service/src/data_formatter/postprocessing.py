# post_processing.py

import logging
from tqdm import tqdm
import json
import os
import sys
from typing import Optional, Dict, Any, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.file_handler import read_input_file, output_2_jsonl, load_record
from utils.validation import load_schema, validate_record, is_english
from utils.load_config import load_config
from providers import ProviderFactory  # Ensure providers are properly structured
from utils.retry_handler import retry
from utils.llm_formatter import LLMFormatter


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostProcessor:
    def __init__(self, config_path: str):
        self.config = load_config(config_path)
        self.postprocessing_schema = load_schema('config/schemas/postprocessing_schema.yaml')
        self.llm_formatter=LLMFormatter

    def process_record(self, record) -> None:
        """ Process a single record. """
        # Postprocessing steps
        self.fact_check(record)
        self.language_check(record)
        self.document_check(record)

        # Validate Postprocessed Data
        if not validate_record(record.to_dict(), self.postprocessing_schema):
            logger.warning(f"Postprocessed record ID {record.record_id} failed validation.")
            return
        
        # Log successful processing
        logger.info(f"Record ID {record.record_id} postprocessed successfully.")

    def fact_check(self, record):
        """ Use LLM to fact-check the record. """
        pass # Placeholder

    def language_check(self, record):
        """ Check language and translate if necessary. """
        if is_english(record.title) or is_english(record.content):
            self.llm_formatter.translate(record)
            

    def document_check(self, record):
        """ Check if content refers to a document and update the document_id. """
        content = record.content
        document_id, document_name, score = self.find_best_matching_document(content)
        if document_id:
            record.document_id = document_id  # Update the record with the found document ID
            record.source = document_name
            logger.info(f"document_id {document_id} added with a score of {score}")

    def find_best_matching_document(self, record) -> Tuple[str, str, float]:
        """ Find the best matching document based on content. """
        mentions = extract_document_mentions(record.content)
        issue_date = extract_issue_date(record.content)
        best_score = 0.0
        best_doc_id = None
        best_file_name = None

        for mention in mentions:
            for doc in self.documents:  # Ensure documents are loaded or passed to this method
                score = calculate_matching_score(doc, mention, issue_date)
                if score > best_score:
                    best_score = score
                    best_doc_id = doc['id'] 
                    best_file_name = doc['file_name']  # Adjust based on your CSV column names

        return best_doc_id, best_file_name, best_score

    def call_llm_for_fact_check(self, original_data, preprocessed_data):
        """ Placeholder for LLM fact-checking call. """
        # Implement the call to your LLM provider here and return the result
        return "Fact check result"
