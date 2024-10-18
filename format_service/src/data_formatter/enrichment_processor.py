# enrichment_processor.py

import pandas as pd
import logging
import json
from typing import List, Dict, Any, Optional
from utils.validation import validate_record
from utils.file_handler import read_file_content
from utils.llm_formatter import LLMFormatter
from utils.record import Record

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnrichmentProcessor:
    def __init__(self, config: Dict[str, Any], documents_df: pd.DataFrame, prompts_path: str = "config/schemas/prompts.yaml"):
        """
        Initialize the EnrichmentProcessor with configuration, documents dataframe, and prompts.

        :param config: Configuration dictionary loaded by load_config().
        :param documents_df: DataFrame containing metadata of legal documents.
        :param prompts_path: Path to the YAML file containing prompts.
        """
        self.config = config
        self.documents_df = documents_df
        self.llm_formatter = LLMFormatter(config=self.config, prompts_path=prompts_path)
        logger.info("EnrichmentProcessor initialized.")

    def split_document(self, document_path: str) -> List[str]:
        """
        Read the document and split it into articles or paragraphs.

        Args:
            document_path: Path to the legal document.

        Returns:
            A list of text chunks.
        """
        content = read_file_content(document_path)
        # Implement splitting logic based on document structure
        chunks = self._split_into_chunks(content)
        logger.debug(f"Split document '{document_path}' into {len(chunks)} chunks.")
        return chunks

    def _split_into_chunks(self, content: str) -> List[str]:
        """
        Split the document content into manageable chunks.

        Args:
            content: The full text of the document.

        Returns:
            A list of text chunks.
        """
        # Example: Split by articles using regex
        import re
        pattern = r'Article\s+\d+[\.,]?\s+'
        chunks = re.split(pattern, content)
        # Remove empty strings and strip whitespace
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        return chunks

    def enrich_chunk(self, chunk_text: str) -> Dict[str, Any]:
        """
        Use the LLM to extract main topic, applicability, generate title/question, and assign categories.

        Args:
            chunk_text: The text of the article or paragraph.

        Returns:
            A dictionary with the extracted information.
        """
        formatted_output = self.llm_formatter.format_text(raw_text=chunk_text, mode="enrichment")
        if not formatted_output:
            logger.error("Enrichment failed or returned empty output.")
            return {}

        enriched_data = self._parse_llm_response(formatted_output)
        return enriched_data

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the LLM response to extract structured data.

        Args:
            response: Raw response text from the LLM.

        Returns:
            A dictionary with structured data.
        """
        enriched_data = {}
        lines = response.split('\n')
        for line in lines:
            if line.startswith('Main Topic:'):
                enriched_data['Main Topic'] = line.replace('Main Topic:', '').strip()
            elif line.startswith('Applicability:'):
                enriched_data['Applicability'] = line.replace('Applicability:', '').strip()
            elif line.startswith('Generated Title:'):
                enriched_data['Generated Title'] = line.replace('Generated Title:', '').strip()
            elif line.startswith('Suggested Categories:'):
                categories = line.replace('Suggested Categories:', '').strip()
                enriched_data['Assigned Categories'] = [cat.strip() for cat in categories.split(',')]
        return enriched_data

    def process_documents(self) -> pd.DataFrame:
        """
        Process all documents in the dataframe and enrich them.

        Returns:
            A new dataframe with enriched data.
        """
        enriched_records = []
        for idx, row in self.documents_df.iterrows():
            logger.info(f"Processing Document ID: {row['Document ID']}")
            chunks = self.split_document(row['Document Path'])
            for chunk_idx, chunk in enumerate(chunks, start=1):
                enriched_data = self.enrich_chunk(chunk)
                if not enriched_data:
                    logger.warning(f"Enrichment failed for Document ID: {row['Document ID']}, Chunk: {chunk_idx}")
                    continue

                # Create a new record with enriched data
                record = {
                    'Category': row['Category'],
                    'Document ID': row['Document ID'],
                    'Hierarchy Level': row['Hierarchy Level'],
                    'Document Path': row['Document Path'],
                    'Parent Document ID': row['Parent Document ID'],
                    'Chunk ID': f"{row['Document ID']}.{chunk_idx}",
                    'Chunk Text': chunk,
                    'Main Topic': enriched_data.get('Main Topic', ''),
                    'Applicability': enriched_data.get('Applicability', ''),
                    'Generated Title': enriched_data.get('Generated Title', ''),
                    'Assigned Categories': enriched_data.get('Assigned Categories', []),
                    'Processing Timestamp': pd.Timestamp.now(),
                    'Validation Status': None  # To be updated after validation
                }

                # Validate the enriched record
                is_valid = validate_record(record=record, mode="postprocessing", config=self.config)
                record['Validation Status'] = is_valid

                if is_valid:
                    enriched_records.append(record)
                else:
                    logger.warning(f"Validation failed for Document ID: {row['Document ID']}, Chunk: {chunk_idx}")

        enriched_df = pd.DataFrame(enriched_records)
        logger.info(f"Enriched dataframe contains {len(enriched_df)} records.")
        return enriched_df
