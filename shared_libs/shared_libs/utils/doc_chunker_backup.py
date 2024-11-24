import os
import re
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

# ----------------------------
# Configuration
# ----------------------------
# Define all possible hierarchical markers with their regex patterns
HIERARCHY_MARKERS = {
    'chapter': re.compile(
        r'^\s*(?P<chapter_marker>Chương\s+(?P<chapter_value>\w+))(?:\s*[-.]?\s*(?P<chapter_title>.*))?$',
        re.IGNORECASE | re.MULTILINE | re.UNICODE
    ),
    'article': re.compile(
        r'^\s*(?P<article_marker>Điều\s+(?P<article_value>\d+))(?:\s*[-.]?\s*(?P<article_title>.*))?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'clause': re.compile(
        r'^\s*(?P<clause_marker>(?P<clause_value>\d+))\s*[-.)]?(?:\s+(?P<clause_title>.+))?$',
        re.MULTILINE
    ),
    'point': re.compile(
        r'^\s*(?P<point_marker>(?P<point_value>[^\W\d_]))\s*[-.)]?(?:\s+(?P<point_title>.+))?$',
        re.MULTILINE | re.UNICODE
    ),
}

# Define the default hierarchy order
DEFAULT_HIERARCHY_ORDER = ['chapter', 'article', 'clause', 'point']


# ----------------------------
# Helper Functions
# ----------------------------

def extract_text_from_txt(file_path):
    """
    Extracts text from a .txt file.
    
    Args:
        file_path (str): Path to the .txt file.
        
    Returns:
        str: Extracted text.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        logger.info(f"Extracted text from TXT file: {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error reading TXT file {file_path}: {e}")
        return ""

def extract_text_from_docx(file_path):
    """
    Extracts text from a .docx file, including text inside tables,
    preserving the order of paragraphs and tables as in the original document,
    and ensuring each table cell is on its own line.

    Args:
        file_path (str): Path to the .docx file.

    Returns:
        str: Extracted text.
    """
    import docx
    try:
        doc = docx.Document(file_path)
        full_text = []

        for block in iter_block_items(doc):
            if isinstance(block, docx.text.paragraph.Paragraph):
                if block.text.strip():
                    full_text.append(block.text.strip())
            elif isinstance(block, docx.table.Table):
                # Extract text from table
                full_text.append("<table>")
                for row in block.rows:
                    full_text.append("<tr>")
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        if cell_text:
                            # Add each cell content as a separate line
                            full_text.append(f"<td>{cell_text}</td>")
                    full_text.append("</tr>")
                full_text.append("</table>")

        text = '\n'.join(full_text)
        logger.info(f"Extracted text from DOCX file: {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error reading DOCX file {file_path}: {e}")
        return ""


def iter_block_items(parent):
    """
    Generate a reference to each paragraph and table child within parent, in document order.

    Args:
        parent: The parent document or element.

    Yields:
        Each child paragraph and table in document order.
    """
    import docx
    from docx.oxml.ns import qn
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    from docx.table import _Cell, Table
    from docx.text.paragraph import Paragraph

    if isinstance(parent, docx.document.Document):
        parent_element = parent.element.body
    elif isinstance(parent, _Cell):
        parent_element = parent._tc
    else:
        raise ValueError("Invalid parent type")

    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)



def extract_text_from_pdf(file_path):
    """
    Extracts text from a .pdf file.
    
    Args:
        file_path (str): Path to the .pdf file.
        
    Returns:
        str: Extracted text.
    """
    import PyPDF2

    try:
        reader = PyPDF2.PdfReader(file_path)
        text = ""
        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            extracted = page.extract_text()
            if extracted:
                text += extracted + '\n'
        logger.info(f"Extracted text from PDF file: {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error reading PDF file {file_path}: {e}")
        return ""

def extract_text_from_html(file_path):
    """
    Extracts text from a .html file.
    
    Args:
        file_path (str): Path to the .html file.
        
    Returns:
        str: Extracted text.
    """
    from bs4 import BeautifulSoup
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'lxml')
        text = soup.get_text(separator='\n')
        logger.info(f"Extracted text from HTML file: {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error reading HTML file {file_path}: {e}")
        return ""

def determine_file_type(file_path):
    """
    Determines the file type based on its extension.
    
    Args:
        file_path (str): Path to the file.
        
    Returns:
        str: File type ('txt', 'docx', 'pdf', 'html') or 'unsupported'.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    if ext == '.txt':
        return 'txt'
    elif ext == '.docx':
        return 'docx'
    elif ext == '.pdf':
        return 'pdf'
    elif ext in ['.html', '.htm']:
        return 'html'
    else:
        return 'unsupported'

def extract_text(file_path):
    """
    Extracts text from a file based on its type.
    
    Args:
        file_path (str): Path to the file.
        
    Returns:
        str: Extracted text.
    """
    file_type = determine_file_type(file_path)
    if file_type == 'txt':
        return extract_text_from_txt(file_path)
    elif file_type == 'docx':
        return extract_text_from_docx(file_path)
    elif file_type == 'pdf':
        return extract_text_from_pdf(file_path)
    elif file_type == 'html':
        return extract_text_from_html(file_path)
    else:
        logger.warning(f"Unsupported file type for file: {file_path}")
        return ""

def detect_hierarchy(content):
    """
    Detects hierarchy markers in the content, excluding table contents.

    Args:
        content (str): The content to analyze.

    Returns:
        list: A list of detected hierarchy markers.
    """
    detected_markers = set()

    # Remove table contents for hierarchy detection
    content_without_tables = remove_table_contents(content)
    lines = content_without_tables.split('\n')

    for line in lines:
        line = line.strip()
        for marker_name, pattern in HIERARCHY_MARKERS.items():
            if marker_name in detected_markers:
                continue  # Skip if already detected
            if pattern.match(line):
                detected_markers.add(marker_name)
                break  # Move to next line after finding a match

    # Remove 'part' and 'section' if they are not adjacent to 'chapter'
    if 'chapter' not in detected_markers:
        detected_markers.discard('part')
        detected_markers.discard('section')

    return list(detected_markers)



def assign_hierarchy_levels(detected_markers):
    hierarchy_mapping = {}
    level = 1
    for marker in DEFAULT_HIERARCHY_ORDER:
        if marker in detected_markers:
            hierarchy_mapping[marker] = level
            level += 1
    return hierarchy_mapping

def adjust_title_and_content(section):
    if section['title'] and not section['content']:
        section['content'] = section['title']
        section['title'] = ''
    for subsection in section.get('subsections', []):
        adjust_title_and_content(subsection)

def parse_hierarchy(content, hierarchy_mapping, doc_id):
    sections = []
    stack = []
    last_pos = 0

    # Create a combined regex pattern
    combined_pattern_parts = []
    for marker in hierarchy_mapping:
        pattern = HIERARCHY_MARKERS[marker]
        combined_pattern_parts.append(f'(?P<{marker}>{pattern.pattern})')
    combined_pattern = re.compile('|'.join(combined_pattern_parts), re.IGNORECASE | re.MULTILINE | re.UNICODE)

    matches = list(combined_pattern.finditer(content))

    for idx, match in enumerate(matches):
        start, end = match.span()
        level = None
        title = ""
        header = ""
        marker_type = ""
        marker_value = ""
        marker_part = ""

        # Determine which marker matched
        for marker in hierarchy_mapping:
            if match.group(marker):
                level = hierarchy_mapping[marker]
                matched_text = match.group(marker)
                match_details = HIERARCHY_MARKERS[marker].match(matched_text)
                if match_details:
                    # Extract marker text, value, and title
                    marker_text = match_details.group(f'{marker}_marker').strip()
                    marker_value = match_details.group(f'{marker}_value').strip()
                    title_text = match_details.group(f'{marker}_title')
                    # Assign header and title
                    header = marker_text
                    if title_text:
                        title = title_text.strip()
                    else:
                        title = ""
                    # If title is empty, treat the entire line as content
                    if not title:
                        content_line = matched_text.strip()
                    else:
                        content_line = ""
                    # Add prefixes as needed
                    if marker == 'clause':
                        header = f"Khoản {marker_text}"
                    elif marker == 'point':
                        header = f"Điểm {marker_text}"
                    marker_type = marker

                    # Build the marker_part for this section
                    if marker_type == 'chapter':
                        marker_part = f'ch{marker_value}'
                    elif marker_type == 'article':
                        marker_part = f'art{int(marker_value):03d}'
                    elif marker_type == 'clause':
                        marker_part = f'cl_{int(marker_value):02d}'
                    elif marker_type == 'point':
                        marker_part = f'pt_{marker_value}'
                    else:
                        marker_part = f'{marker_type}_{marker_value}'
                break

        if level is None:
            continue  # No matching marker

        # Assign text between the last position and the current marker to the content of the previous section
        if last_pos < start:
            text = content[last_pos:start].strip()
            if text and stack:
                # Assign text to the content of the previous section
                stack[-1]['section']['content'] += '\n' + text if stack[-1]['section']['content'] else text

        # Adjust the stack
        while stack and stack[-1]['level'] >= level:
            stack.pop()

        # Build the current markers list for ID generation from the stack
        current_markers = [entry['marker_part'] for entry in stack] + [marker_part]

        # Build the id
        unique_id = doc_id + ''.join('_' + m for m in current_markers)

        # Create a new section
        new_section = {
            'level': level,
            'header': header,
            'title': title,
            'content': content_line if content_line else '',
            'subsections': [],
            'id': unique_id,
        }

        # Add the section to the appropriate parent
        if stack:
            parent_section = stack[-1]['section']
            parent_section['subsections'].append(new_section)
        else:
            sections.append(new_section)

        # Push the new section onto the stack
        stack.append({
            'level': level,
            'section': new_section,
            'marker_part': marker_part,
        })

        # Update last_pos
        last_pos = end

    # Handle any remaining text after the last match
    if last_pos < len(content):
        remaining_text = content[last_pos:].strip()
        if remaining_text and stack:
            stack[-1]['section']['content'] += '\n' + remaining_text if stack[-1]['section']['content'] else remaining_text

    # Remove 'level' keys from sections
    def remove_level(section):
        if 'level' in section:
            del section['level']
        for subsection in section.get('subsections', []):
            remove_level(subsection)

    for section in sections:
        remove_level(section)

    # Adjust title and content
    for section in sections:
        adjust_title_and_content(section)

    return sections

def extract_doc_id(segment_text):
    """
    Extracts the document ID from the segment text.

    Args:
        segment_text (str): The text of the segment.

    Returns:
        str: Extracted document ID or an empty string if not found.
    """
    elements = segment_text.split("\n")
    for element in elements[:30]:  # Search within the first 30 lines
        element = element.strip()
        # Skip table tags
        if element in ("<table>", "</table>", "<tr>", "</tr>"):
            continue
        # If element is a table cell
        if element.startswith("<td>") and element.endswith("</td>"):
            element_text = element[4:-5].strip()
        else:
            element_text = element

        match = re.search(r"(?:Số|Luật số)[:\s]*([^\s,;]+)", element_text)
        if match:
            return match.group(1).strip()
    return ""

def create_structured_json(doc_number, doc_id, doc_name, articles):
    """
    Creates a structured JSON object for a document segment (main document or appendix).

    Args:
        doc_number (int): Document segment number (1 for main document, >1 for appendices).
        doc_id (str): Document ID.
        doc_name (str): Document name extracted from the first two paragraphs.
        articles (list): List of articles with structured sections.

    Returns:
        dict: Structured JSON object.
    """
    return {
        "doc_number": doc_number,
        "doc_id": doc_id,
        "doc_name": doc_name,
        "articles": articles
    }

# Parse the hierarchy and get the root sections and stack entries
def parse_document(content, hierarchy_mapping, doc_id):
    # Parse the hierarchy and assign IDs during parsing
    sections = parse_hierarchy(content, hierarchy_mapping, doc_id)
    return sections
def extract_main_doc_name(segment_text):
    """
    Extracts the document name for the main document, ignoring text inside <table> tags.

    Args:
        segment_text (str): The text of the main document.

    Returns:
        str: Extracted document name.
    """
    # Remove text inside <table> tags
    cleaned_text = remove_table_content(segment_text)
    # Extract paragraphs
    paragraphs = [p.strip() for p in cleaned_text.split("\n") if p.strip()]
    # Return the first two paragraphs as the document name
    return " ".join(paragraphs[:2]) if paragraphs else ""

def extract_appendix_doc_name(segment_text):
    """
    Extracts the document name for an appendix, ignoring text inside <table> tags.

    Args:
        segment_text (str): The text of the appendix.

    Returns:
        str: Extracted document name.
    """
    # Remove text inside <table> tags
    cleaned_text = remove_table_content(segment_text)
    # Extract paragraphs
    paragraphs = [p.strip() for p in cleaned_text.split("\n") if p.strip()]
    # Return the first two paragraphs as the document name
    return " ".join(paragraphs[:2]) if paragraphs else ""

def remove_table_content(text):
    """
    Removes text content inside <table> tags from the given text.

    Args:
        text (str): The input text containing potential <table> tags.

    Returns:
        str: Text with <table> content removed.
    """
    import re
    # Regex pattern to match <table>...</table> and remove it
    cleaned_text = re.sub(r"<table>.*?</table>", "", text, flags=re.DOTALL)
    return cleaned_text


def process_raw_file(file_path, output_json_path):
    """
    Processes a single raw text file and converts it into a structured JSON file,
    handling segmentation of the main document, appendices, and forms/templates.

    Args:
        file_path (str): Path to the raw text file.
        output_json_path (str): Path to save the structured JSON file.
    """
    try:
        # Extract file name from the file path
        doc_filename = os.path.basename(file_path)

        # Extract text from the file
        raw_text = extract_text(file_path)
        if not raw_text:
            logger.warning(f"No text extracted from file: {file_path}")
            return
        
        # Sanitize raw text
        sanitized_text = sanitize_content(raw_text)

        # Split the text into segments (main document and appendices)
        segments = identify_and_segment_document(sanitized_text)

        documents = []  # To hold all structured documents for this file
        main_doc_id = None  # To track the main document ID
        for segment in segments:
            doc_number = segment['doc_number']
            segment_text = segment['content']

            # Extract the document ID
            if doc_number == 1:
                main_doc_id = extract_doc_id(segment_text)  # Use the main document's ID
                appendix_base_id = main_doc_id  # Preserve the base ID for appendices
            else:
                appendix_id = f"{appendix_base_id}_appendix_{doc_number:02d}"

            # Extract the document name
            if doc_number == 1:
                doc_name = extract_main_doc_name(segment_text)
            else:
                doc_name = extract_appendix_doc_name(segment_text)

            # Detect hierarchical markers in the segment
            detected_markers = detect_hierarchy(segment_text)
            segment_id = main_doc_id if doc_number == 1 else appendix_id
            if not detected_markers:
                logger.warning(f"No hierarchical markers detected in segment {doc_number}.")
                structured_sections = [{
                    'header': '',
                    'title': '',
                    'content': segment_text,
                    'subsections': []
                }]
            else:
                hierarchy_mapping = assign_hierarchy_levels(detected_markers)
                structured_sections = parse_document(segment_text, hierarchy_mapping, segment_id)

            # Detect forms/templates within appendices
            if doc_number > 1:
                forms = detect_forms_in_appendix(segment_text)
                appendix_content = structured_sections
                structured_sections = []  # Reorganize appendices with forms

                paragraphs = segment_text.split("\n")
                for form in forms:
                    form_id = f"{appendix_id}_{form['form_id']}"
                    form_paragraphs = "\n".join(paragraphs[form['start']:form['end']])
                    form_markers = detect_hierarchy(form_paragraphs)
                    form_hierarchy = assign_hierarchy_levels(form_markers)
                    form_sections = parse_document(form_paragraphs, form_hierarchy, form_id)
                    form_sections = clean_redundant_content(form_sections)  # Clean form content
                    structured_sections.append({
                        "header": f"Form {form['form_id']}",
                        "title": "",
                        "content": form['text'],
                        "id": form_id,
                        "subsections": form_sections
                    })

                # Add remaining appendix content that isn't part of forms
                non_form_content = [p for idx, p in enumerate(paragraphs) if all(idx < form['start'] or idx >= form['end'] for form in forms)]
                if non_form_content:
                    appendix_content = clean_redundant_content(appendix_content)  # Clean appendix content
                    structured_sections.append({
                        "header": "Appendix Content",
                        "title": "",
                        "content": "\n".join(non_form_content),
                        "id": appendix_id,
                        "subsections": appendix_content
                    })

            # Clean redundant content in structured sections
            structured_sections = clean_redundant_content(structured_sections)

            # Create structured JSON for the segment
            document_json = {
                "doc_number": doc_number,
                "doc_id": main_doc_id if doc_number == 1 else appendix_id,
                "doc_name": doc_name,
                "articles": structured_sections
            }
            documents.append(document_json)

        # Write all structured documents to the output JSON file
        with open(output_json_path, 'w', encoding='utf-8') as outfile:
            json.dump({
                "doc_filename": doc_filename,
                "documents": documents
            }, outfile, ensure_ascii=False, indent=4)

        logger.info(f"Successfully processed file: {file_path} and saved to {output_json_path}")

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")


def reconstruct_table(content, indent_level):
    """
    Reconstructs table data from tagged content.

    Args:
        content (str): The content containing table tags.
        indent_level (int): Current indentation level for formatting.

    Returns:
        str: The reconstructed table as text.
    """
    indent = "    " * indent_level
    text = ""
    lines = content.split('\n')
    row_cells = []
    for line in lines:
        line = line.strip()
        if line == "<table>" or line == "</table>":
            if line == "</table>":
                text += "\n"  # Add a newline after the table
            continue
        elif line == "<tr>":
            row_cells = []
            continue
        elif line == "</tr>":
            # Output the row cells
            text += indent + ' | '.join(row_cells) + "\n"
            row_cells = []
            continue
        elif line.startswith("<td>") and line.endswith("</td>"):
            cell_content = line[4:-5].strip()
            row_cells.append(cell_content)
        else:
            # Regular content outside of table tags
            text += f"{indent}{line}\n"
    return text

def find_section_by_id(section, section_id):
    """
    Recursively searches for a section with the specified id.

    Args:
        section (dict): The current section to search.
        section_id (str): The id of the section to find.

    Returns:
        dict or None: The section with the matching id, or None if not found.
    """
    if section.get('id') == section_id:
        return section

    for subsection in section.get('subsections', []):
        result = find_section_by_id(subsection, section_id)
        if result:
            return result

    return None

def retrieve_section_text(section_id, json_file_path):
    """
    Retrieves and reconstructs the text of a specific section by its id, with redundancy to retrieve 
    based on partial id if the full id is not found.

    Args:
        section_id (str): The id of the section to retrieve.
        json_file_path (str): Path to the structured JSON file.

    Returns:
        str: The reconstructed text of the section and its subsections, or an empty string if not found.
    """
    if not os.path.exists(json_file_path):
        logger.error(f"JSON file does not exist: {json_file_path}")
        return ""

    logger.info(f"Loading JSON from file: {json_file_path}")

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    documents = data.get("documents", [])
    if not documents:
        logger.warning("No documents found in JSON.")
        return ""

    # Extract the document ID and unique marker from the section ID
    doc_id, _, unique_marker = section_id.partition('_')

    # Traverse documents to find the section with the specified id
    for document in documents:
        if document.get("doc_id") != doc_id:
            continue

        articles = document.get("articles", [])

        # Primary search: Look for the exact section ID
        for article in articles:
            section = find_section_by_id(article, section_id)
            if section:
                return process_section(section, include_full_hierarchy=False)

        # Fallback search: Look for the section using only the unique marker
        for article in articles:
            section = find_section_by_partial_id(article, unique_marker)
            if section:
                logger.warning(f"Exact match for id '{section_id}' not found. Using fallback match '{unique_marker}'.")
                return process_section(section, include_full_hierarchy=False)

    logger.warning(f"Section with id '{section_id}' not found, even with fallback.")
    return ""

def find_section_by_partial_id(section, unique_marker):
    """
    Recursively searches for a section with a partial unique marker.

    Args:
        section (dict): The current section to search.
        unique_marker (str): The unique marker (e.g., 'art003') to find.

    Returns:
        dict or None: The section with the matching unique marker, or None if not found.
    """
    if section.get('id', '').endswith(f"_{unique_marker}"):
        return section

    for subsection in section.get("subsections", []):
        result = find_section_by_partial_id(subsection, unique_marker)
        if result:
            return result

    return None


def find_section_by_id(section, section_id):
    """
    Recursively searches for a section with the specified id.

    Args:
        section (dict): The current section to search.
        section_id (str): The id of the section to find.

    Returns:
        dict or None: The section with the matching id, or None if not found.
    """
    if section.get('id') == section_id:
        return section

    for subsection in section.get('subsections', []):
        result = find_section_by_id(subsection, section_id)
        if result:
            return result

    return None

def process_section(section, indent_level=0, include_full_hierarchy=False, parent_headers=None):
    """
    Processes a section or subsection to reconstruct text.
    
    Args:
        section (dict): The current section or subsection.
        indent_level (int): Current indentation level for formatting.
        include_full_hierarchy (bool): Whether to include the full hierarchy for each section.
        parent_headers (list): List of parent headers for constructing full references.
    
    Returns:
        str: The reconstructed text for this section.
    """
    indent = "    " * indent_level
    text = ""

    header = section.get("header", "")
    title = section.get("title", "")
    content = section.get("content", "")

    # Initialize parent_headers if not provided
    if parent_headers is None:
        parent_headers = []

    # Build the full reference if include_full_hierarchy is True
    if include_full_hierarchy:
        current_headers = parent_headers + [header] if header else parent_headers
        full_reference = ', '.join(filter(None, reversed(current_headers)))
        if full_reference:
            text += f"{indent}{full_reference}\n"
    else:
        if header:
            text += f"{indent}{header}\n"

    # Add title if present
    if title:
        text += f"{indent}{title}\n"

    # Add content
    if content:
        text += f"{indent}{content}\n"

    # Process subsections
    for subsection in section.get("subsections", []):
        text += process_section(subsection, indent_level + 1, include_full_hierarchy, parent_headers + [header])

    return text

import re

def identify_and_segment_document(content):
    """
    Identifies and segments a document into the main document and appendices based on rules.

    Args:
        content (str): The raw text of the document.

    Returns:
        list: A list of segments, each representing a part of the document with doc_number.
    """
    segments = []  # To store segments of the document
    current_segment = {"doc_number": 1, "content": ""}
    paragraphs = content.split("\n")
    inside_table = False

    for idx, para in enumerate(paragraphs):
        para = para.strip()

        # Rule 1: Check for "Nơi nhận:" and "Lưu:" in a table
        if inside_table or ("<table>" in para and "</table>" in para):
            if re.search(r"Nơi nhận:.*Lưu:", para, re.IGNORECASE):
                # End the current segment and start a new one
                if current_segment["content"].strip():
                    segments.append(current_segment)
                current_segment = {"doc_number": len(segments) + 1, "content": ""}
                continue

        # Rule 2: Check for "Phụ lục" and Roman numerals or similar markers
        if re.match(r"Phụ lục\s+[IVXLCDM\-A-Za-z0-9\.]*", para, re.IGNORECASE):
            points = 40  # Initial point for potential appendix marker
            # Check the next 3 paragraphs or the nearest table
            for offset in range(1, 4):
                if idx + offset < len(paragraphs):
                    next_para = paragraphs[idx + offset].strip()
                    # Normalize text for matching
                    normalized = next_para.lower().replace(" ", "")
                    if "banhànhkèm" in normalized or "cộnghòaxãhội" in normalized:
                        points += 10
                        break

            # Check previous 3 paragraphs
            for offset in range(1, 4):
                if idx - offset >= 0:
                    prev_para = paragraphs[idx - offset].strip()
                    normalized = prev_para.lower().replace(" ", "")
                    if "nơinhận:" in normalized or "ghihọtên" in normalized:
                        points += 10
                        break

            # If points >= 50%, treat it as a new appendix
            if points >= 50:
                if current_segment["content"].strip():
                    segments.append(current_segment)
                current_segment = {"doc_number": len(segments) + 1, "content": ""}
                continue

        # Add the current paragraph to the current segment
        current_segment["content"] += para + "\n"

    # Add the last segment if it contains content
    if current_segment["content"].strip():
        segments.append(current_segment)

    return segments

def clean_redundant_content(sections):
    """
    Removes redundant content in higher-level sections if it is already present in lower-level sections.
    Also removes lower-level titles from the content of higher-level sections.

    Args:
        sections (list): The list of sections (articles, clauses, etc.) to clean up.

    Returns:
        list: The cleaned-up sections.
    """
    for section in sections:
        if 'subsections' in section and section['subsections']:
            # Recursively clean subsections first
            clean_redundant_content(section['subsections'])

            # Aggregate all subsection titles and content
            lower_level_contents = []
            for subsection in section['subsections']:
                if subsection.get('content'):
                    lower_level_contents.append(subsection['content'].strip())
                if subsection.get('title'):
                    lower_level_contents.append(subsection['title'].strip())

            # Deduplicate content in the current section
            if section.get('content'):
                current_content = section['content']
                for lower_content in lower_level_contents:
                    # Remove exact matches, accounting for normalization
                    lower_content_normalized = lower_content.strip()
                    current_content = current_content.replace(lower_content_normalized, "").strip()

                # Update the section's content
                section['content'] = current_content

    return sections

def remove_table_contents(content):
    """
    Removes all content within <table>...</table> tags.

    Args:
        content (str): The original content containing potential table tags.

    Returns:
        str: Content with table sections removed.
    """
    import re
    table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)
    return table_pattern.sub('', content)


def sanitize_content(content):
    """
    Sanitizes the content to ensure it does not interfere with JSON structure.
    Escapes special characters like ' and ".

    Args:
        content (str): The raw content to sanitize.

    Returns:
        str: Sanitized content.
    """
    if not content:
        return content

    # Escape backslashes, then escape double quotes and single quotes
    content = content.replace("\\", "\\\\")  # Escape backslashes first
    content = content.replace("\"", "\\\"")  # Escape double quotes
    content = content.replace("'", "\\'")    # Escape single quotes



    return content


# ----------------------------
# Main Function
# ----------------------------

def convert_raw_to_structured_json(raw_file_path, output_json_path):
    """
    Converts a single raw text file into a structured JSON file.
    
    Args:
        raw_file_path (str): Path to the raw text file (*.txt, *.docx, *.html, *.pdf).
        output_json_path (str): Path to save the structured JSON file.
    """
    
    logger.info(f"Starting conversion for file: {raw_file_path}")
    
    process_raw_file(raw_file_path, output_json_path)
    
    logger.info(f"Conversion completed for file: {raw_file_path}")

def reconstruct_text(json_file_path):
    """
    Reconstructs raw text from a structured JSON file.

    Args:
        json_file_path (str): Path to the structured JSON file.

    Returns:
        str: The reconstructed raw text.
    """
    if not os.path.exists(json_file_path):
        logger.error(f"JSON file does not exist: {json_file_path}")
        return ""

    logger.info(f"Loading JSON from file: {json_file_path}")

    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    full_text = ""

    documents = data.get("documents", [])
    if not documents:
        logger.warning("No documents found in JSON.")
        return full_text

    for document in documents:
        articles = document.get("articles", [])
        for article in articles:
            # Pass include_full_hierarchy=True for full references
            full_text += process_section(article, include_full_hierarchy=True)

        # Optionally, add separators between documents
        full_text += "\n" + "-" * 80 + "\n\n"

    return full_text



def process_folder(input_folder, output_folder):
    """
    Processes all files in the input folder (and its subfolders), converts them to structured JSON,
    and saves them in the output folder while preserving the folder hierarchy.

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
            input_file_path = os.path.join(root, file_name)
            output_file_path = os.path.join(output_subfolder, f"{file_name}.json")

            try:
                # Convert file to structured JSON
                logger.info(f"Processing file: {input_file_path}")
                convert_raw_to_structured_json(input_file_path, output_file_path)
            except Exception as e:
                logger.error(f"Failed to process file {input_file_path}: {e}")


import os

def retrieve_section_text_from_folder(section_id, folder_path):
    """
    Searches for a specific section by its id in all JSON files within a folder (and subfolders),
    and reconstructs its text if found.

    Args:
        section_id (str): The id of the section to retrieve.
        folder_path (str): Path to the folder containing JSON files.

    Returns:
        str: The reconstructed text of the section and its subsections if found, or a message if not found.
    """
    if not os.path.exists(folder_path):
        logger.error(f"Folder does not exist: {folder_path}")
        return f"Folder not found: {folder_path}"

    # Iterate over all files in the folder and subfolders
    for root, _, files in os.walk(folder_path):
        for file_name in files:
            if file_name.endswith(".json"):
                json_file_path = os.path.join(root, file_name)
                logger.info(f"Searching for section id '{section_id}' in file: {json_file_path}")
                # Try to retrieve the section from this file
                section_text = retrieve_section_text(section_id, json_file_path)
                if section_text:
                    logger.info(f"Section id '{section_id}' found in file: {json_file_path}")
                    return section_text

    # If not found in any file, return a message
    logger.warning(f"Section id '{section_id}' not found in any JSON file within folder: {folder_path}")
    return f"Section id '{section_id}' not found in any JSON file within folder: {folder_path}"

def detect_forms_in_appendix(segment_text):
    """
    Detects forms/templates within an appendix based on scoring rules.

    Args:
        segment_text (str): The text of the appendix.

    Returns:
        list: A list of detected forms/templates with their text, positions, and unique IDs.
    """
    forms = []
    paragraphs = segment_text.split("\n")
    form_counter = 1  # To assign unique IDs for forms/templates
    start_idx = None

    for idx, para in enumerate(paragraphs):
        para = para.strip()
        points = 0

        # Rule 1: Contains "mẫusố" (normalized)
        if "mẫusố" in para.lower().replace(" ", ""):
            points += 40

        # Rule 2: Prior paragraph has "banhànhkèm" (normalized)
        if idx > 0:
            prev_para = paragraphs[idx - 1].strip().lower().replace(" ", "")
            if "banhànhkèm" in prev_para:
                points += 10

        # Rule 3: Next paragraph is in CAPITAL
        if idx < len(paragraphs) - 1:
            next_para = paragraphs[idx + 1].strip()
            if next_para.isupper():
                points += 10

	# Rule 4: Prior text/paragraph is a table
        if idx > 0:
            prev_para = paragraphs[idx - 1].strip()
            if "<table>" in prev_para or "</table>" in prev_para:
                points += 10

        # Rule 5: After text/paragraph is a table
        if idx < len(paragraphs) - 1:
            next_para = paragraphs[idx + 1].strip()
            if "<table>" in next_para or "</table>" in next_para:
                points += 10

        # Rule 6: After text/paragraph contains "cộnghòaxãhội" (normalized)
        if idx < len(paragraphs) - 1:
            next_para = paragraphs[idx + 1].strip().lower().replace(" ", "")
            if "cộnghòaxãhội" in next_para:
                points += 10

        # If total points >= 60, classify it as a form/template
        if points >= 50:
            if start_idx is not None:
                # Close the previous form
                forms[-1]['end'] = idx
            form_text = para
            forms.append({
                "form_id": f"form_{form_counter:02d}",
                "text": form_text,
                "start": idx,
                "end": None  # To be filled when the next form or end of appendix is found
            })
            form_counter += 1
            start_idx = idx

    # Close the last form if open
    if forms and forms[-1]['end'] is None:
        forms[-1]['end'] = len(paragraphs)

    return forms



# ----------------------------
# Example Usage
# ----------------------------


if __name__ == "__main__":
    # Example file paths (Adjust these paths accordingly)
    raw_file = r'format_service\src\data\raw\1. DOANH NGHIỆP\1.4.2. 122_2020_TT-BTC_converted_with_appendix.docx'        # Replace with your raw file path
    output_json = r'format_service\src\data\raw\1. DOANH NGHIỆP\1.4.2. 122_2020_TT-BTC_converted_with_appendix.json'      # Replace with your desired JSON output path
    
    # Step 1: Convert raw file to structured JSON
    convert_raw_to_structured_json(raw_file, output_json)
    
    # Step 2: Reconstruct text from JSON
    full_text = reconstruct_text(output_json)
    
    # Step 3: Print or Save the Reconstructed Text
    if full_text:
        # Option 1: Print to Console
        # print(full_text)
        
        # Option 2: Write to a Text File (Uncomment if needed)
        reconstructed_text_path = r'format_service\src\data\raw\1. DOANH NGHIỆP\1.4.2. 122_2020_TT-BTC_converted_with_appendix.txt'
        with open(reconstructed_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"Reconstructed text has been written to '{reconstructed_text_path}'")
    else:
        print("No text was reconstructed.")