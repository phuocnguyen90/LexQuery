from shared_libs.utils.doc_chunker import process_folder, retrieve_section_text_from_folder,identify_and_segment_document
from shared_libs.models.record_model import Record
from typing import List, Optional
import json

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



input_folder=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\raw\1. DOANH NGHIỆP'
output_folder=r'C:\Users\PC\git\legal_qa_rag\format_service\src\data\preprocessed\1. DOANH NGHIỆP'


if __name__ == "__main__":
    # process the whole folder
    process_folder(input_folder, output_folder)

    # find a section by id
    section_id ="01/2021/TT-BKHĐT_appendix_101"
    section_text = retrieve_section_text_from_folder(section_id,output_folder)

    if section_text:
        print("Reconstructed Text for Section ID:", section_id)
        print(section_text)
    else:
        print(f"No text found for section id: {section_id}")