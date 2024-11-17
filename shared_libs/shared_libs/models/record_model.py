import json
import logging
import pandas as pd
from typing import Any, Dict, List, Optional
from shared_libs.utils.file_handler import generate_unique_id

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Record:
    """
    A class to represent a single record for RAG implementation.
    This class stores core fields and metadata fields of a record.
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
        """
        self.record_id = record_id
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
        """
        try:
            return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error converting Record to JSON: {e}")
            return ""

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> Optional['Record']:
        """
        Create a Record instance from a JSON dictionary.
        """

        try:
            return cls(
                record_id=data.get('record_id') or generate_unique_id(),
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
