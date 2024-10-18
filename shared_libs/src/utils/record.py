# utils/record.py

import sys
import os

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
import logging
from typing import Any, Dict, List, Optional, Union
import re
import pandas as pd
from utils.llm_formatter import LLMFormatter
import uuid

from utils.validation import detect_text_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Record:
    """
    A class to represent and handle a single record for RAG implementation.
    """
    
    def __init__(
        self,
        record_id: str,
        document_id: Optional[str],
        title: str,
        content: str,
        chunk_id: Optional[str],
        hierarchy_level: Optional[int] = None,
        categories: Optional[List[str]] = None,
        relationships: Optional[List[str]] = None,
        published_date: Optional[str] = None,
        source: Optional[List[str]] = None,
        processing_timestamp: Optional[str] = None,
        validation_status: Optional[bool] = None,
        language: Optional[str] = 'vi',
        summary: Optional[str] = ''
    ):
        """
        Initialize a Record object with core and metadata fields.
        
        :param record_id: Unique identifier for the Record.
        :param document_id: Unique identifier for the source document or Q&A pair.
        :param title: Primary title or summary of the record.
        :param content: Main content used for RAG.
        :param chunk_id: Unique identifier for each content chunk.
        :param hierarchy_level: Structural level of the content.
        :param categories: List of categories or tags assigned.
        :param relationships: List of relationships with other records.
        :param published_date: Publication or creation date.
        :param source: Origin of the record.
        :param processing_timestamp: Timestamp when the record was processed.
        :param validation_status: Indicates if the record passed validation checks.
        :param language: Language of the content.
        :param summary: Optional brief overview of the content.
        """
        self.record_id = record_id  # New unique identifier
        self.document_id = document_id
        self.title = title
        self.content = content
        self.chunk_id = chunk_id
        self.hierarchy_level = hierarchy_level
        self.categories = categories if categories is not None else []
        self.relationships = relationships if relationships is not None else []
        self.published_date = published_date
        self.source = source
        self.processing_timestamp = processing_timestamp if processing_timestamp else pd.Timestamp.now().isoformat()
        self.validation_status = validation_status
        self.language = language
        self.summary = summary

        

    @classmethod
    def from_tagged_text(cls, text: str, record_type: str = "DOC") -> Optional['Record']:
        """
        Initialize a Record object from tagged text.
        
        :param text: The raw tagged text string.
        :param record_type: Type of the record ('QA' or 'DOC').
        :return: Record object or None if parsing fails.
        """
        record = cls.parse_record(record_str=text, return_type="record", record_type=record_type)
        if record:
            logger.info(f"Record ID {record.record_id} created successfully from tagged text.")
            return record
        else:
            logger.error("Failed to create Record from tagged text.")
            return None

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> Optional['Record']:
        """
        Create a Record instance from a JSON dictionary.
        """
        try:
            return cls(
                record_id=data.get('record_id') or data.get('id') or generate_unique_id(),
                document_id=data.get('document_id'),
                title=data['title'],
                content=data['content'],
                chunk_id=data.get('chunk_id'),
                hierarchy_level=data.get('hierarchy_level', 1),
                categories=data.get('categories', []),
                relationships=data.get('relationships', []),
                published_date=data.get('published_date'),
                source=data.get('source'),
                processing_timestamp=data.get('processing_timestamp', pd.Timestamp.now().isoformat()),
                validation_status=data.get('validation_status', False),
                language=data.get('language', 'vi'),
                summary=data.get('summary', '')
            )
        except KeyError as e:
            logger.error(f"Missing required field: {e}")
            return None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['Record']:
        """
        Initialize a Record object from a dictionary.
        
        :param data: Dictionary representing the record.
        :return: Record object or None if required fields are missing.
        """
        try:
            record_id = data['record_id']
            document_id = data.get('document_id')
            title = data['title']
            content = data['content']
            chunk_id = data.get('chunk_id')
            hierarchy_level = data.get('hierarchy_level')
            categories = data.get('categories', [])
            relationships = data.get('relationships', [])
            published_date = data.get('published_date')
            source = data.get('source')
            processing_timestamp = data.get('processing_timestamp')
            validation_status = data.get('validation_status')
            language = data.get('language', 'vi')
            summary = data.get('summary', '')
            
            return cls(
                record_id=record_id if record_id else generate_unique_id("REC"),
                document_id=document_id,
                title=title,
                content=content,
                chunk_id=chunk_id,
                hierarchy_level=hierarchy_level,
                categories=categories,
                relationships=relationships,
                published_date=published_date,
                source=source,
                processing_timestamp=processing_timestamp,
                validation_status=validation_status,
                language=language,
                summary=summary
            )
        except KeyError as e:
            logger.error(f"Missing required field in data dictionary: {e}")
            return None
        except Exception as e:
            logger.error(f"Error initializing Record from dict: {e}")
            return None

    @classmethod
    def from_unformatted_text(cls, text: str, llm_processor:LLMFormatter, record_type: str = "DOC") -> Optional['Record']:
        """
        Initialize a Record object from unformatted text by using an LLM to structure it.
        
        :param text: Unformatted raw text.
        :param llm_processor: A callable that takes raw text and returns structured text.
        :param record_type: Type of the record ('QA' or 'DOC').
        :return: Record object or None if processing fails.
        """
        try:
            # Use the LLM to format the unformatted text
            formatted_text = llm_processor.format_text(text,"tagged",record_type)
            if not formatted_text:
                logger.error("LLM failed to format the unformatted text.")
                return None
            # Attempt to parse the formatted text as tagged text
            return cls.from_tagged_text(formatted_text, record_type=record_type)
        except Exception as e:
            logger.error(f"Error processing unformatted text into Record: {e}")
            return None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the Record instance to a dictionary.
        """
        return {
            "record_id": self.record_id,
            "document_id": self.document_id,
            "title": self.title,
            "content": self.content,
            "chunk_id": self.chunk_id,
            "hierarchy_level": self.hierarchy_level,
            "categories": self.categories,
            "relationships": self.relationships,
            "published_date": self.published_date,
            "source": self.source,
            "processing_timestamp": self.processing_timestamp,
            "validation_status": self.validation_status,
            "language": self.language,
            "summary": self.summary
        }
    def to_json(self) -> str:
        """
        Convert the Record object to a JSON string.
        
        :return: JSON string representation of the Record.
        """
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error converting Record to JSON: {e}")
            return ""
    
    def get(self, key: Any, *args, default: Any = None) -> Any:
        """
        Retrieve a value from the Record similar to dict.get(), with support for list indices.
    
        :param key: The attribute name to retrieve or a list representing the path.
        :param args: Optional indices for list attributes.
        :param default: The value to return if the key/index is not found.
        :return: The retrieved value or default.
        """
        try:
            # If key is a list or tuple, treat it as a path
            if isinstance(key, (list, tuple)):
                keys = key
                if not keys:
                    logger.debug(f"Empty key path provided. Returning default: {default}")
                    return default
                first_key, *remaining_keys = keys
                value = getattr(self, first_key, default)
                if value is default:
                    logger.debug(f"Attribute '{first_key}' not found. Returning default: {default}")
                    return default
                for k in remaining_keys:
                    if isinstance(value, list):
                        if isinstance(k, int) and 0 <= k < len(value):
                            value = value[k]
                        else:
                            logger.debug(f"Index {k} out of range for attribute '{first_key}'. Returning default: {default}")
                            return default
                    elif isinstance(value, dict):
                        value = value.get(k, default)
                        if value is default:
                            logger.debug(f"Key '{k}' not found in dictionary. Returning default: {default}")
                            return default
                    else:
                        logger.debug(f"Attribute '{first_key}' is neither a list nor a dict. Cannot traverse key '{k}'. Returning default: {default}")
                        return default
                return value
            else:
                # Existing functionality
                value = getattr(self, key, default)
                if value is default:
                    logger.debug(f"Attribute '{key}' not found. Returning default: {default}")
                    return default

                for index in args:
                    if isinstance(value, list):
                        if isinstance(index, int) and 0 <= index < len(value):
                            value = value[index]
                        else:
                            logger.debug(f"Index {index} out of range for attribute '{key}'. Returning default: {default}")
                            return default
                    else:
                        logger.debug(f"Attribute '{key}' is not a list. Cannot apply index {index}. Returning default: {default}")
                        return default

                return value

        except Exception as e:
            record_id = self.record_id if hasattr(self, 'record_id') else 'N/A'
            logger.error(f"Error in get method for record ID {record_id}: {e}")
            return default
        

    @classmethod
    def parse_record(
        cls,
        record_str: str,
        return_type: str = "record",
        record_type: str = "DOC",
        llm_formatter: Optional[Any] = None  # Adjusted type hint for flexibility
    ) -> Optional[Union['Record', Dict[str, Any], str]]:
        """
        Parse a record string into a Record object, dictionary, or JSON string.

        The method determines the format of the input (JSON, tagged, or unformatted),
        processes it accordingly, and returns the desired output type.

        :param record_str: The raw input string representing the record.
        :param return_type: The type of output desired.
                            - "record" (default): Returns a Record object.
                            - "dict": Returns a dictionary.
                            - "json": Returns a JSON string.
        :param record_type: Type of the record ('QA' or 'DOC') to prefix the record_id accordingly.
        :param llm_formatter: An instance of LLMFormatter for formatting unformatted text.
        :return: Record object, dictionary, JSON string, or None if parsing fails.
        """
        try:
            # Detect the input text type
            text_type = detect_text_type(record_str)
            logger.debug(f"Detected text type: {text_type}")

            # If input is unformatted, use LLMFormatter to convert to tagged format
            if text_type == "unformatted":
                if not llm_formatter:
                    logger.error("LLMFormatter instance is required to process unformatted text.")
                    return None
                logger.info("Converting unformatted text to tagged format using LLMFormatter.")
                formatted_text = llm_formatter.format_text(raw_text=record_str, mode="tagged")
                if not formatted_text:
                    logger.error("LLMFormatter failed to format unformatted text.")
                    return None
                record_str = formatted_text  # Update record_str to tagged format
                text_type = "tagged"  # Update text_type after conversion
                logger.debug("Successfully converted unformatted text to tagged format.")

            # Process based on text_type
            if text_type == "json":
                # Parse JSON and create Record
                try:
                    data = json.loads(record_str)
                    logger.debug("Input is detected as JSON format.")
                    record = cls.from_json(data)
                    if record:
                        logger.info(f"Record parsed successfully from JSON with ID: {record.record_id}")
                    else:
                        logger.warning("Failed to create Record from JSON data.")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decoding error: {e}")
                    return None

            elif text_type == "tagged":
                # Extract fields using regular expressions with flexible ID patterns
                record_id_match = re.search(r'<id=([A-Za-z]{2,3}_[A-Za-z0-9]+)>', record_str)
                document_id_match = re.search(r'<document_id=([A-Za-z]{2,3}_[A-Za-z0-9]+)>', record_str)
                chunk_id_match = re.search(r'<chunk_id=([A-Za-z]{2,3}_[A-Za-z0-9]+)>', record_str)
                title_match = re.search(r'<title>(.*?)</title>', record_str, re.DOTALL)
                content_match = re.search(r'<content>(.*?)</content>', record_str, re.DOTALL)
                hierarchy_level_match = re.search(r'<hierarchy_level=(\d+)>', record_str)
                published_date_match = re.search(r'<published_date>(.*?)</published_date>', record_str, re.DOTALL)
                categories_match = re.search(r'<categories>(.*?)</categories>', record_str, re.DOTALL)
                relationships_match = re.search(r'<relationships>(.*?)</relationships>', record_str, re.DOTALL)
                source_match = re.search(r'<source>(.*?)</source>', record_str, re.DOTALL)
                processing_timestamp_match = re.search(r'<processing_timestamp>(.*?)</processing_timestamp>', record_str, re.DOTALL)
                validation_status_match = re.search(r'<validation_status>(True|False)</validation_status>', record_str, re.DOTALL)
                language_match = re.search(r'<language>(.*?)</language>', record_str, re.DOTALL)
                summary_match = re.search(r'<summary>(.*?)</summary>', record_str, re.DOTALL)

                # Initialize variables with default or extracted values
                record_id = record_id_match.group(1).strip() if record_id_match else generate_unique_id(record_type)
                document_id = document_id_match.group(1).strip() if document_id_match else ("N/A" if record_type == "QA" else generate_unique_id("DOC"))
                chunk_id = chunk_id_match.group(1).strip() if chunk_id_match else ("N/A" if record_type == "QA" else generate_unique_id("CHNK"))
                title = title_match.group(1).strip() if title_match else None
                content = content_match.group(1).strip() if content_match else None
                hierarchy_level = int(hierarchy_level_match.group(1)) if hierarchy_level_match else 1  # Default to 1 if missing
                published_date = published_date_match.group(1).strip() if published_date_match else None
                categories_str = categories_match.group(1).strip() if categories_match else ''
                categories = re.findall(r'<(.*?)>', categories_str) if categories_str else []
                relationships_str = relationships_match.group(1).strip() if relationships_match else ''
                relationships = re.findall(r'<(.*?)>', relationships_str) if relationships_str else []
                source = source_match.group(1).strip() if source_match else None
                processing_timestamp = processing_timestamp_match.group(1).strip() if processing_timestamp_match else pd.Timestamp.now().isoformat()
                validation_status = True if validation_status_match and validation_status_match.group(1) == 'True' else False
                language = language_match.group(1).strip() if language_match else 'vi'
                summary = summary_match.group(1).strip() if summary_match else ''

                # Check for mandatory fields: title and content
                if not title or not content:
                    logger.error("Missing mandatory fields: 'title' and/or 'content'. Cannot create Record.")
                    return None

                # Create a dictionary representation
                record_dict = {
                    "record_id": record_id,
                    "document_id": document_id,
                    "title": title,
                    "content": content,
                    "chunk_id": chunk_id,
                    "hierarchy_level": hierarchy_level,
                    "categories": categories,
                    "relationships": relationships,
                    "published_date": published_date,
                    "source": source,
                    "processing_timestamp": processing_timestamp,
                    "validation_status": validation_status,
                    "language": language,
                    "summary": summary
                }

                # Create Record instance
                record = cls.from_json(record_dict)
                if record:
                    logger.info(f"Record parsed successfully from tagged text with ID: {record.record_id}")
                else:
                    logger.warning("Failed to create Record from tagged text data.")

            else:
                logger.error(f"Unsupported text type: {text_type}")
                return None

            # Return based on return_type
            if return_type == "record":
                return record
            elif return_type == "dict":
                return record_dict
            elif return_type == "json":
                return json.dumps(record_dict, ensure_ascii=False, indent=2)
            else:
                logger.error(f"Invalid return_type '{return_type}' specified. Choose from 'record', 'dict', 'json'.")
                return None

        except Exception as e:
            logger.error(f"Error parsing text into Record object: {e}")
            return None

def generate_record_id(record_type: str) -> str:
    """
    Generate a unique record_id based on the record type.
    
    :param record_type: Type of the record ('QA' or 'DOC').
    :return: A unique record_id string.
    """
    prefix = "QA" if record_type == "QA" else "DOC"
    unique_part = str(uuid.uuid4()).replace('-', '')[:8].upper()  # Short unique string
    return f"{prefix}_{unique_part}"

def generate_document_id() -> str:
    """
    Generate a unique document_id.
    
    :return: A unique document_id string.
    """
    unique_part = str(uuid.uuid4()).replace('-', '')[:8].upper()
    return f"DOC_{unique_part}"

def generate_chunk_id(document_id: str) -> str:
    """
    Generate a unique chunk_id based on the document_id.
    
    :param document_id: The document_id to associate with the chunk.
    :return: A unique chunk_id string.
    """
    unique_part = str(uuid.uuid4()).replace('-', '')[:8].upper()
    return f"{document_id}_CHNK_{unique_part}"

def generate_unique_id(prefix: str = "REC") -> str:
    """
    Generate a unique ID for records without an existing ID.

    :param prefix: Prefix for the unique ID (e.g., "QA", "DOC", "REC").
    :return: A unique ID string.
    """
    unique_part = uuid.uuid4().hex[:8].upper()
    return f"{prefix}_{unique_part}"