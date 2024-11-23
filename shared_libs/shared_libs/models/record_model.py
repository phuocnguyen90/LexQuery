import json
import logging
import pandas as pd
from typing import Any, Dict, List, Optional

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
# Function to calculate hierarchy level based on document type and other features
def calculate_hierarchy_level(section_type: str, parent_level: Optional[int] = None) -> int:
    if section_type == "chapter":
        return 1
    elif section_type == "article":
        return 2
    elif section_type == "clause":
        return 3
    elif section_type == "point":
        return 4
    elif section_type == "appendix":
        return 5
    else:
        return (parent_level or 0) + 1

# Adapter function to convert JSON structure to a list of Record objects
def json_to_records(json_file_path: str) -> List[Record]:
    records = []

    # Load the simplified JSON
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for document in data.get("documents", []):
        doc_id = document.get("doc_id")
        doc_name = document.get("doc_name")

        # Process Chapters and Articles
        for chapter in document.get("chapters", []):
            chapter_id = chapter.get("chapter_id")
            chapter_title = chapter.get("text", "")

            # Create a record for the chapter
            records.append(Record(
                record_id=chapter_id,
                document_id=doc_id,
                title=chapter_title,
                content=chapter_title,  # Assuming title is used as content for chapter-level records
                chunk_id=chapter_id,
                hierarchy_level=calculate_hierarchy_level("chapter")
            ))

            # Process Articles within the Chapter
            for article in chapter.get("articles", []):
                article_id = article.get("article_id")
                article_title = article.get("text", "")
                clauses = article.get("clauses", [])
                article_content = article_title

                if not clauses:  # If there are no clauses, treat the whole article as a single record
                    records.append(Record(
                        record_id=article_id,
                        document_id=doc_id,
                        title=article_title,
                        content=article_content,
                        chunk_id=article_id,
                        hierarchy_level=calculate_hierarchy_level("article", 1)  # Parent level is 1 (Chapter)
                    ))
                else:
                    # If there are clauses, create a record for the article title
                    records.append(Record(
                        record_id=article_id,
                        document_id=doc_id,
                        title=article_title,
                        content=article_title,
                        chunk_id=article_id,
                        hierarchy_level=calculate_hierarchy_level("article", 1)  # Parent level is 1 (Chapter)
                    ))

                    # Process Clauses within the Article
                    for clause in clauses:
                        clause_id = clause.get("clause_id")
                        clause_title = clause.get("text", "")
                        points = clause.get("points", [])
                        clause_content = clause_title

                        if not points:  # If there are no points, treat the clause as a single record
                            records.append(Record(
                                record_id=clause_id,
                                document_id=doc_id,
                                title=clause_title,
                                content=clause_content,
                                chunk_id=clause_id,
                                hierarchy_level=calculate_hierarchy_level("clause", 2)  # Parent level is 2 (Article)
                            ))
                        else:
                            # If there are points, create a record for the clause title
                            records.append(Record(
                                record_id=clause_id,
                                document_id=doc_id,
                                title=clause_title,
                                content=clause_title,
                                chunk_id=clause_id,
                                hierarchy_level=calculate_hierarchy_level("clause", 2)  # Parent level is 2 (Article)
                            ))

                            # Process Points within the Clause
                            for point in points:
                                point_id = point.get("point_id")
                                point_title = point.get("text", "")
                                records.append(Record(
                                    record_id=point_id,
                                    document_id=doc_id,
                                    title=point_title,
                                    content=point_title,
                                    chunk_id=point_id,
                                    hierarchy_level=calculate_hierarchy_level("point", 3)  # Parent level is 3 (Clause)
                                ))

        # Process Appendices
        for appendix in document.get("appendices", []):
            appendix_id = appendix.get("appendix_id")
            appendix_title = appendix.get("doc_name", "")
            appendix_content = appendix.get("content", "")
            records.append(Record(
                record_id=appendix_id,
                document_id=doc_id,
                title=appendix_title,
                content=appendix_content,
                chunk_id=appendix_id,
                hierarchy_level=calculate_hierarchy_level("appendix")
            ))

    return records

import hashlib
import base64

def generate_unique_id(title: str, content: str, prefix: str = "REC") -> str:
    """
    Generate a unique ID based on content and title to ensure consistency.

    :param title: Title of the record.
    :param content: Content of the record.
    :param prefix: Prefix for the unique ID.
    :return: A unique ID string.
    """
    # Concatenate the title and content
    combined_string = f"{title}|{content}"
    
    # Generate a SHA-256 hash of the combined string
    hash_object = hashlib.sha256(combined_string.encode('utf-8'))
    
    # Encode to base64 and take the first 10 characters
    unique_part = base64.urlsafe_b64encode(hash_object.digest()).decode('utf-8')[:10]

    # Return the unique ID with the prefix
    return f"{prefix}_{unique_part}"