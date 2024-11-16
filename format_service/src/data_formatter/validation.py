# utils/validation.py

import json
import yaml
import logging
import re
from langdetect import detect
from shared_libs.llm_providers.groq_provider import GroqProvider
from jsonschema import validate, ValidationError
from typing import Dict, Any, Optional
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# logging.getLogger(__name__)
def load_schema(schema_path):
    """
    Load a YAML schema from a file.
    
    :param schema_path: Path to the YAML schema file.
    :return: Parsed schema as a Python dictionary.
    """
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = yaml.safe_load(f)
        logger.info(f"Loaded schema from '{schema_path}'.")
        return schema
    except Exception as e:
        logger.error(f"Error loading schema '{schema_path}': {e}")
        raise

def validate_record(record: Any, schema_path: str, mode: str = 'default', config: Optional[Dict[str, Any]] = None) -> bool:
    """
    Validate a single record against the provided JSON schema based on the mode.
    
    :param record: The record to validate. Can be a dictionary or a JSON string.
    :param schema_path: Path to the JSON schema file.
    :param mode: Optional mode for validation ("preprocessing", "postprocessing"). Defaults to 'default'.
    :param config: Configuration dictionary loaded by load_config(). Required if mode is specified.
    :return: True if valid, False otherwise.
    """
    try:
        # Step 1: Load the appropriate schema based on mode
        if mode == 'preprocessing':
            if config is None:
                logger.error("Configuration must be provided for preprocessing mode.")
                return False
            # Load pre_processing_schema.yml
            schema_full = load_schema('config/schemas/preprocessing_schema.yaml')
            if schema_full is None:
                logger.error("Failed to load 'preprocessing_schema.yaml'.")
                return False
            # Extract the JSON schema part (exclude 'pre_process_requirements')
            # Assuming 'pre_process_requirements' is a separate key
            json_schema = {k: v for k, v in schema_full.items() if k != 'pre_process_requirements'}
            if not json_schema:
                logger.error("JSON schema not found in 'preprocessing_schema.yaml'.")
                return False

        elif mode == 'postprocessing':
            if config is None:
                logger.error("Configuration must be provided for postprocessing mode.")
                return False
            # Load postprocessing_schema.yml
            schema_full = load_schema('config/schemas/postprocessing_schema.yml')
            if schema_full is None:
                logger.error("Failed to load 'postprocessing_schema.yml'.")
                return False
            # Extract the JSON schema part (exclude 'post_process_requirements' if exists)
            json_schema = {k: v for k, v in schema_full.items() if k != 'post_process_requirements'}
            if not json_schema:
                logger.error("JSON schema not found in 'postprocessing_schema.yml'.")
                return False

        elif mode == 'default':
            # Use the provided schema_path directly
            json_schema = load_schema(schema_path)
            if json_schema is None:
                logger.error(f"Failed to load schema from '{schema_path}'.")
                return False
        else:
            logger.error(f"Invalid mode '{mode}' specified for validation.")
            return False

        # Step 2: Ensure record is a dictionary
        if not isinstance(record, dict):
            logger.debug("Record is not a dictionary. Attempting to convert from JSON string.")
            try:
                record = json.loads(record)
                logger.debug("Record successfully converted to dictionary with JSON module.")
            except json.JSONDecodeError as jde:
                logger.error(f"Failed to decode JSON for record: {jde.msg}")
                return False

        # Step 3: If in postprocessing mode, send to LLM for compliance
        if mode == 'postprocessing':
            logger.debug(f"Sending record ID {record.get('id', 'N/A')} to LLM for compliance check.")
            # Assuming 'post_process_requirements' exists in the schema_full
            post_process_requirements = schema_full.get('post_process_requirements', {})
            is_compliant = llm_validate(record, post_process_requirements, config)
            if not is_compliant:
                logger.error(f"LLM validation failed for record ID {record.get('id', 'N/A')}.")
                return False
            logger.debug(f"LLM validation passed for record ID {record.get('id', 'N/A')}.")

        # Step 4: Validate the record against the JSON schema
        validate(instance=record, schema=json_schema)

        # Step 5: Extract 'id' for logging, if available
        record_id = record.get('id', 'N/A')
        logger.info(f"Record ID {record_id} passed validation in mode '{mode}'.")
        return True

    except ValidationError as ve:
        # Extract 'id' for logging, if available
        record_id = record.get('id', 'N/A') if isinstance(record, dict) else 'N/A'
        logger.error(f"Validation error for record ID {record_id} in mode '{mode}': {ve.message}")
        return False
    except Exception as e:
        # General exception handling
        record_id = record.get('id', 'N/A') if isinstance(record, dict) else 'N/A'
        logger.error(f"Unexpected error during validation for record ID {record_id} in mode '{mode}': {e}")
        return False


def mask_api_key(api_key):
    """
    Mask the API key by replacing all characters except the last four with '***'.
    
    :param api_key: The original API key as a string.
    :return: Masked API key.
    """
    try:
        if not isinstance(api_key, str):
            raise TypeError("API key must be a string.")
        if len(api_key) <= 4:
            # If API key is too short, mask entirely
            return 'invalid'
        else:
            return '***' + api_key[-4:]
    except Exception as e:
        logger.error(f"Error masking API key: {e}")
        return '***'
    
def llm_validate(record: Dict[str, Any], requirements: Dict[str, Any], config: Dict[str, Any]) -> bool:
    """
    Validate the record against the requirements using the GroqProvider.

    :param record: The record to validate as a dictionary.
    :param requirements: The JSON schema or requirements to validate against.
    :param config: The configuration dictionary loaded by load_config().
    :return: True if compliant, False otherwise.
    """
    try:
        logger.debug("Initializing GroqProvider for LLM validation.")
        # Initialize GroqProvider with config and requirements
        groq_provider = GroqProvider(config=config, requirements=requirements)
        
        logging.debug("Processing record with GroqProvider.")
        processed_record_json = groq_provider.process_record(record)
        
        if processed_record_json is None:
            logger.error("GroqProvider failed to process the record.")
            return False
        
        # Optionally, you can further process or validate the `processed_record_json` if needed
        # For now, we'll assume that a successful processing indicates compliance
        logger.debug("GroqProvider successfully processed the record.")
        return True

    except Exception as e:
        logger.error(f"LLM validation failed with exception: {e}")
        return False
    
def detect_text_type(text: str) -> str:
    """
    Detect the format of the input text.

    :param text: The input text string.
    :return: A string indicating the text type: 'json', 'tagged', or 'unformatted'.
    """
    # Attempt to parse as JSON
    try:
        json.loads(text)
        logger.debug("Input detected as JSON format.")
        return "json"
    except json.JSONDecodeError:
        logger.debug("Input is not JSON format.")
    
    # Check for mandatory tags
    has_title = re.search(r'<title>.*?</title>', text, re.DOTALL)
    has_content = re.search(r'<content>.*?</content>', text, re.DOTALL)
    
    if has_title and has_content:
        logger.debug("Input detected as tagged text format.")
        return "tagged"
    
    logger.debug("Input detected as unformatted text.")
    return "unformatted"

def is_english(text):
    try:
        return detect(text) == 'en'
    except Exception as e:
        return False