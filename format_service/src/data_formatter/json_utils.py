import json
import os
from bs4 import BeautifulSoup
from shared_libs.utils.doc_chunker import retrieve_section_text


from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import AppConfigLoader

# Configure logger
try:
    config = AppConfigLoader()
except Exception as e:
    print(f"Failed to load configuration: {e}")
    

# Load the logger
 
logger = Logger.get_logger(module_name=__name__)

def count_words(text):
    """
    Count words in a given text.

    Args:
        text (str): The input text.

    Returns:
        int: The word count.
    """
    return len(text.split())

def flatten_table(content):
    """
    Converts table content in HTML format to a plain text, readable structure.
    
    Args:
        content (str): HTML content of the table.
    
    Returns:
        str: Flattened table content as plain text.
    """
    soup = BeautifulSoup(content, "html.parser")
    rows = []

    for tr in soup.find_all("tr"):
        row = []
        for td in tr.find_all("td"):
            row.append(td.get_text(strip=True))
        rows.append(" | ".join(row))

    return "\n".join(rows)

def process_appendix_content(content):
    """
    Process appendix content by flattening any table tags and converting to plain text.
    
    Args:
        content (str): Content of the appendix, potentially containing HTML tables.
    
    Returns:
        str: Plain text representation of the appendix.
    """
    # Flatten tables
    content = flatten_table(content)

    # Additional cleanup if needed (remove extra tags, etc.)
    return content.strip()

def generate_combined_structure(json_file_path, output_file_path):
    """
    Generate a combined structure JSON file:
        - Main document (`doc_number == 1`) is processed with detailed structure.
        - Appendices (`doc_number > 1`) are flattened and rearranged as appendices of the main document.

    Args:
        json_file_path (str): Path to the detailed input JSON file.
        output_file_path (str): Path to save the simplified JSON file.
    """
    if not os.path.exists(json_file_path):
        raise FileNotFoundError(f"Input file not found: {json_file_path}")

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    simple_structure = {"doc_filename": data.get("doc_filename"), "documents": []}

    main_document = None
    appendices = []

    for document in data.get("documents", []):
        doc_number = document.get("doc_number")
        doc_id = document.get("doc_id")
        doc_name = document.get("doc_name")

        if doc_number == 1:
            # Process main document
            chapters = []

            for chapter in document.get("articles", []):
                if not chapter.get("subsections"):
                    continue  # Skip if no subsections (no articles)

                # Construct chapter text from header and content
                chapter_text = f"{chapter.get('header', '').strip()} {chapter.get('content', '').strip()}".strip()

                articles = []
                for article in chapter.get("subsections", []):
                    article_id = article.get("id")
                    # Use directly reconstructed text to avoid searching
                    article_text = directly_reconstruct_text(article, include_full_hierarchy=False)
                    article_word_count = count_words(article_text)

                    if article_word_count < 300:
                        # Keep the article as a single unit
                        articles.append({"article_id": article_id, "text": article_text})
                    else:
                        # Retain clauses for longer articles but avoid repeating full content
                        article_text = f"{article.get('header', '').strip()} {article.get('title', '').strip()}"
                        clauses = []
                        for clause in article.get("subsections", []):
                            clause_id = clause.get("id")
                            clause_text = directly_reconstruct_text(clause, include_full_hierarchy=False)
                            clause_word_count = count_words(clause_text)

                            if clause_word_count < 300:
                                clauses.append({"clause_id": clause_id, "text": clause_text})
                            else:
                                # Retain points for longer clauses but avoid repeating full content
                                clause_text = f"{clause.get('header', '').strip()} {clause.get('title', '').strip()}"
                                points = []
                                for point in clause.get("subsections", []):
                                    point_id = point.get("id")
                                    point_text = directly_reconstruct_text(point, include_full_hierarchy=False)
                                    points.append({"point_id": point_id, "text": point_text})

                                clauses.append({"clause_id": clause_id, "text": clause_text, "points": points})

                        articles.append({"article_id": article_id, "text": article_text, "clauses": clauses})

                chapters.append({"chapter_id": chapter.get("id"), "text": chapter_text, "articles": articles})

            # Store the main document
            main_document = {
                "doc_id": doc_id,
                "doc_name": doc_name,
                "chapters": chapters
            }
        else:
            # Process appendices (flatten)
            appendix_content = flatten_appendix_content(document)

            # Clean content and append
            appendices.append({
                "appendix_id": doc_id,
                "doc_name": doc_name,
                "content": appendix_content.strip()
            })

    # Combine main document and appendices
    if main_document:
        if appendices:
            main_document["appendices"] = appendices
        simple_structure["documents"].append(main_document)

    # Save the simplified structure to a file
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        json.dump(simple_structure, outfile, ensure_ascii=False, indent=4)

    print(f"Simplified structure saved to: {output_file_path}")


def flatten_appendix_content(document):
    """
    Flattens the content of an appendix by converting its hierarchical structure into plain text.

    Args:
        document (dict): The structured representation of an appendix.

    Returns:
        str: The flattened, plain text content of the appendix.
    """
    flattened_content = ""

    # Iterate over all articles in the document
    for article in document.get("articles", []):
        flattened_table_content=flatten_table(article)
        flattened_content += directly_reconstruct_text(flattened_table_content, include_full_hierarchy=True) + "\n"

    return flattened_content.strip()


def directly_reconstruct_text(section, indent_level=0, include_full_hierarchy=False):
    """
    Directly reconstructs text from a given section without searching.

    Args:
        section (dict): The section to reconstruct text from.
        indent_level (int): The current indentation level for formatting.
        include_full_hierarchy (bool): Whether to include the full hierarchy for each section.

    Returns:
        str: The reconstructed text for this section.
    """
    indent = "    " * indent_level
    text = ""

    header = section.get("header", "")
    title = section.get("title", "")
    content = section.get("content", "")

    # Build the full reference if include_full_hierarchy is True
    if include_full_hierarchy and header:
        text += f"{indent}{header}\n"

    # Add title if present
    if title:
        text += f"{indent}{title}\n"

    # Add content
    if content:
        text += f"{indent}{content}\n"

    # Process subsections recursively
    for subsection in section.get("subsections", []):
        text += directly_reconstruct_text(subsection, indent_level + 1, include_full_hierarchy)

    return text.strip()

def process_folder(input_folder, output_folder):
    """
    Processes all files in the input folder (and its subfolders) that contain 'with_appendix' in their filename,
    converts them to structured JSON, and saves them in the output folder while preserving the folder hierarchy.

    Args:
        input_folder (str): Path to the input folder containing the raw files.
        output_folder (str): Path to the output folder where structured JSON files will be saved.
    """
    for root, _, files in os.walk(input_folder):
        # Compute the relative path from the input folder
        relative_path = os.path.relpath(root, input_folder)
        # Determine the corresponding output folder
        output_subfolder = os.path.join(output_folder, relative_path)
        os.makedirs(output_subfolder, exist_ok=True)

        for file_name in files:
            if "with_appendix" not in file_name:  # Skip files not containing 'with_appendix'
                logger.info(f"Skipping file: {file_name} (does not contain 'with_appendix')")
                continue

            input_file_path = os.path.join(root, file_name)
            output_file_path = os.path.join(output_subfolder, f"{file_name}.json")

            try:
                # Convert file to structured JSON
                logger.info(f"Processing file: {input_file_path}")
                generate_combined_structure(input_file_path, output_file_path)
            except Exception as e:
                logger.error(f"Failed to process file {input_file_path}: {e}")



input_folder=r'format_service\src\data\preprocessed\1. DOANH NGHIỆP'
output_folder=r'format_service\src\data\preprocessed\1. DOANH NGHIỆP\simplified'


if __name__ == "__main__":
    # process the whole folder
    process_folder(input_folder, output_folder)

    