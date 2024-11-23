from shared_libs.utils.doc_chunker import process_folder, retrieve_section_text_from_folder,identify_and_segment_document
from shared_libs.models.record_model import Record, generate_unique_id
from typing import List, Optional
import json


from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import AppConfigLoader

# Configure logger
try:
    config = AppConfigLoader()
except Exception as e:
    print(f"Failed to load configuration: {e}")
   
# Load the logger
 
logger = Logger.get_logger(module_name=__name__) 

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
        return 1
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
            chapter_header = chapter.get("header", "").strip()
            chapter_title = chapter.get("title", "").strip() or chapter.get("content", "").strip()
            chapter_content = chapter.get("content", "").strip()

            # Create a record for the chapter
            records.append(Record(
                record_id=generate_unique_id(title=chapter_title, content=chapter_title, prefix="DOC"),
                document_id=doc_id,
                title=chapter_title,
                content=chapter_content,
                chunk_id=chapter_id,
                hierarchy_level=calculate_hierarchy_level("chapter")
            ))

            # Process Articles within the Chapter
            for article in chapter.get("articles", []):
                article_id = article.get("article_id")
                article_header = article.get("header", "").strip()
                article_title = article.get("title", "").strip() or article.get("content", "").strip()
                article_content = article.get("content", "").strip()

                clauses = article.get("clauses", [])

                if not clauses:  # If there are no clauses, treat the whole article as a single record
                    records.append(Record(
                        record_id=generate_unique_id(title=article_title, content=article_content, prefix="DOC"),
                        document_id=doc_id,
                        title=article_title,
                        content=article_content,
                        chunk_id=article_id,
                        hierarchy_level=calculate_hierarchy_level("article", 1)  # Parent level is 1 (Chapter)
                    ))
                else:
                    # Create a record for the article itself
                    records.append(Record(
                        record_id=generate_unique_id(title=article_title, content=article_title, prefix="DOC"),
                        document_id=doc_id,
                        title=article_title,
                        content=article_content,
                        chunk_id=article_id,
                        hierarchy_level=calculate_hierarchy_level("article", 1)  # Parent level is 1 (Chapter)
                    ))

                    # Process Clauses within the Article
                    for clause in clauses:
                        clause_id = clause.get("clause_id")
                        clause_header = clause.get("header", "").strip()
                        clause_title = clause.get("title", "").strip() or article_title  # If clause title missing, inherit from article
                        clause_content = clause.get("content", "").strip() or article_content

                        points = clause.get("points", [])

                        if not points:  # If there are no points, treat the clause as a single record
                            records.append(Record(
                                record_id=generate_unique_id(title=clause_title, content=clause_content, prefix="DOC"),
                                document_id=doc_id,
                                title=clause_title,
                                content=clause_content,
                                chunk_id=clause_id,
                                hierarchy_level=calculate_hierarchy_level("clause", 2)  # Parent level is 2 (Article)
                            ))
                        else:
                            # Create a record for the clause itself
                            records.append(Record(
                                record_id=generate_unique_id(title=clause_title, content=clause_content, prefix="DOC"),
                                document_id=doc_id,
                                title=clause_title,
                                content=clause_content,
                                chunk_id=clause_id,
                                hierarchy_level=calculate_hierarchy_level("clause", 2)  # Parent level is 2 (Article)
                            ))

                            # Process Points within the Clause
                            for point in points:
                                point_id = point.get("point_id")
                                point_header = point.get("header", "").strip()
                                point_title = point.get("title", "").strip() or clause_title  # If point title missing, inherit from clause
                                point_content = point.get("content", "").strip() or clause_content

                                records.append(Record(
                                    record_id=generate_unique_id(title=point_title, content=point_content, prefix="DOC"),
                                    document_id=doc_id,
                                    title=point_title,
                                    content=point_content,
                                    chunk_id=point_id,
                                    hierarchy_level=calculate_hierarchy_level("point", 3)  # Parent level is 3 (Clause)
                                ))

        # Process Appendices
        for appendix in document.get("appendices", []):
            appendix_id = appendix.get("appendix_id")
            appendix_title = appendix.get("doc_name", "").strip()
            appendix_content = appendix.get("content", "").strip()

            records.append(Record(
                record_id=generate_unique_id(prefix="APPENDIX"),
                document_id=doc_id,
                title=appendix_title,
                content=appendix_content,
                chunk_id=appendix_id,
                hierarchy_level=calculate_hierarchy_level("appendix")
            ))

    return records


import os
def process_folder_to_jsonl(input_folder: str, output_jsonl_path: str):
    """
    Process a folder containing structured JSON files, convert them to records, and save all results in a JSONL file.

    Args:
        input_folder (str): Path to the input folder containing structured JSON files.
        output_jsonl_path (str): Path to save the combined JSONL output.
    """
    # Iterate over all files in the folder and its subfolders
    for root, _, files in os.walk(input_folder):
        for file_name in files:
            if file_name.endswith(".json"):
                json_file_path = os.path.join(root, file_name)
                
                # Convert the current JSON file to records
                try:
                    records = json_to_records(json_file_path)
                    
                    # Write each record to the output JSONL file
                    with open(output_jsonl_path, 'a', encoding='utf-8') as jsonl_file:
                        for record in records:
                            # Convert the Record object to a dictionary and then dump it to JSON
                            record_dict = record.__dict__
                            jsonl_file.write(json.dumps(record_dict, ensure_ascii=False) + '\n')
                            
                    print(f"Processed and added records from: {json_file_path}")
                except Exception as e:
                    print(f"Error processing file {json_file_path}: {e}")

    print(f"All records have been saved to: {output_jsonl_path}")

input_folder=r'format_service\src\data\preprocessed\simplified'
output_jsonl_file=r'format_service\src\data\preprocessed\preprocessed_data.jsonl'



if __name__ == "__main__":
    process_folder_to_jsonl(input_folder, output_jsonl_file)
