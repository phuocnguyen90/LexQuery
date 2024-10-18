# pre_processing.py

import logging
import json
from typing import Optional, Dict, Any

from utils.validation import load_schema, validate_record, mask_api_key
from utils.retry_handler import retry
from utils.record import Record
from utils.llm_formatter import LLMFormatter

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Preprocessor:
    """
    A class to handle the pre-processing and processing of individual records.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Preprocessor with the given configuration.

        :param config: Configuration dictionary.
        """
        self.config = config
        self.llm_formatter = self._initialize_llm_formatter()
        logger.info("Preprocessor initialized with provided configuration.")

        # Load preprocessing schema
        self.preprocessing_schema = self._load_preprocessing_schema()
        self.pre_process_requirements = self.preprocessing_schema.get('pre_process_requirements', [])
        if not self.pre_process_requirements:
            logger.warning("No 'pre_process_requirements' found in the schema.")

    def _initialize_llm_formatter(self) -> LLMFormatter:
        """
        Initialize the LLMFormatter with the given configuration.

        :return: An instance of LLMFormatter.
        """
        try:
            # Reuse the singleton instance
            llm_formatter = LLMFormatter(config=self.config)
            return llm_formatter
        except Exception as e:
            logger.error(f"Failed to initialize LLMFormatter: {e}")
            raise

    def _load_preprocessing_schema(self) -> Dict[str, Any]:
        """
        Load the preprocessing schema from the specified path in the configuration.

        :return: Dictionary representing the preprocessing schema.
        """
        try:
            schema_path = self.config['processing']['schema_paths']['pre_processing_schema']
            schema = load_schema(schema_path)  # Ensure load_schema is properly implemented
            logger.info(f"Preprocessing schema loaded from '{schema_path}'.")
            return schema
        except KeyError as ke:
            logger.error(f"Missing key in configuration: {ke}")
            raise
        except Exception as e:
            logger.error(f"Failed to load preprocessing schema: {e}")
            raise

    def preprocess_record(self, record: Record) -> Record:
        """
        Apply preprocessing steps to a Record.

        :param record: The Record instance to preprocess.
        :return: The preprocessed Record instance.
        """
        try:
            # Example preprocessing steps
            if 'mask_pii' in self.pre_process_requirements:
                original_content = record.content
                record.content = mask_api_key(record.content)
                logger.debug(f"Record ID {record.record_id}: Masked PII.")
                logger.debug(f"Original Content: {original_content}")
                logger.debug(f"Masked Content: {record.content}")

            # Add more preprocessing steps as per requirements
            # Example: clean_text, remove_stopwords, etc.

            return record
        except Exception as e:
            logger.error(f"Error during preprocessing of record ID {record.record_id}: {e}")
            raise

    def process_record(self, record: Record, mode: str) -> Optional[Record]:
        """
        Process a single Record instance by preprocessing, validating, and formatting/enriching it.

        :param record: The Record instance to process.
        :param mode: The processing mode ("enrichment", "formatting", etc.).
        :return: The processed Record instance or None if processing fails.
        """
        try:
            # Preprocess the record
            preprocessed_record = self.preprocess_record(record)
            logger.debug(f"Record ID {preprocessed_record.record_id} preprocessed.")

            # Validate preprocessed data
            schema_path = self.config['processing']['schema_paths']['pre_processing_schema']
            is_valid = validate_record(
                record=preprocessed_record.to_dict(),
                schema_path=schema_path,
                mode="preprocessing",
                config=self.config
            )
            if not is_valid:
                logger.warning(f"Preprocessed record ID {preprocessed_record.record_id} failed validation.")
                return None
            logger.debug(f"Record ID {preprocessed_record.record_id} passed validation.")

            # Format or enrich the record using LLMFormatter
            formatted_output = self.llm_formatter.format_text(
                raw_text=preprocessed_record.content,
                mode=mode,
                record_type=preprocessed_record.record_type if hasattr(preprocessed_record, 'record_type') else None,
                json_schema=self.config.get('processing', {}).get('json_schema', None)
            )

            if not formatted_output:
                logger.warning(f"Formatting failed for record ID {preprocessed_record.record_id}.")
                return None

            # Initialize a new Record object from the formatted output
            processed_record = Record.parse_record(formatted_output)
            if not processed_record:
                logger.error(f"Processed data for record ID {preprocessed_record.record_id} is invalid.")
                return None

            logger.debug(f"Record ID {processed_record.record_id} processed successfully.")
            return processed_record

        except Exception as e:
            logger.error(f"Failed to process record ID {record.record_id}: {e}")
            return None
