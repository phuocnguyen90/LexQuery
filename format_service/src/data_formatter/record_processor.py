import re
import json
import uuid
import logging
from typing import Any, Dict, Optional, Union
from shared_libs.models.record import Record
from llm_formatter import LLMFormatter
from validation import detect_text_type


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecordProcessor:
    """
    A class for processing and creating Record instances from different input formats.
    Handles LLM formatting and parsing logic.
    """

    @classmethod
    def from_tagged_text(cls, text: str, record_type: str = "DOC") -> Optional['Record']:
        """
        Create a Record object from tagged text.
        """
        record = cls.parse_record(record_str=text, return_type="record", record_type=record_type)
        if record:
            logger.info(f"Record ID {record.record_id} created successfully from tagged text.")
            return record
        else:
            logger.error("Failed to create Record from tagged text.")
            return None

    @classmethod
    def from_unformatted_text(cls, text: str, llm_processor: LLMFormatter, record_type: str = "DOC") -> Optional['Record']:
        """
        Create a Record object from unformatted text by using an LLM to structure it.
        """
        try:
            formatted_text = llm_processor.format_text(text, "tagged", record_type)
            if not formatted_text:
                logger.error("LLM failed to format the unformatted text.")
                return None
            return cls.from_tagged_text(formatted_text, record_type=record_type)
        except Exception as e:
            logger.error(f"Error processing unformatted text into Record: {e}")
            return None

    @classmethod
    def parse_record(
        cls,
        record_str: str,
        return_type: str = "record",
        record_type: str = "DOC",
        llm_formatter: Optional[LLMFormatter] = None
    ) -> Optional[Union[Record, Dict[str, Any], str]]:
        """
        Parse a record string into a Record object, dictionary, or JSON string.
        """
        try:
            text_type = detect_text_type(record_str)
            logger.debug(f"Detected text type: {text_type}")

            if text_type == "unformatted":
                if not llm_formatter:
                    logger.error("LLMFormatter instance is required to process unformatted text.")
                    return None
                formatted_text = llm_formatter.format_text(record_str, mode="tagged")
                if not formatted_text:
                    logger.error("LLMFormatter failed to format unformatted text.")
                    return None
                record_str = formatted_text
                text_type = "tagged"
                logger.debug("Successfully converted unformatted text to tagged format.")

            if text_type == "json":
                try:
                    data = json.loads(record_str)
                    return Record.from_json(data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decoding error: {e}")
                    return None

            elif text_type == "tagged":
                # Extract fields using regular expressions
                # ... (Regex-based extraction code as in the original implementation)
                record_dict = {
                    # Populate fields using regex matches
                }
                return Record.from_json(record_dict)

            else:
                logger.error(f"Unsupported text type: {text_type}")
                return None

        except Exception as e:
            logger.error(f"Error parsing text into Record object: {e}")
            return None
def generate_unique_id(prefix: str = "REC") -> str:
    """
    Generate a unique ID for records without an existing ID.

    :param prefix: Prefix for the unique ID (e.g., "QA", "DOC", "REC").
    :return: A unique ID string.
    """
    unique_part = uuid.uuid4().hex[:8].upper()
    return f"{prefix}_{unique_part}"