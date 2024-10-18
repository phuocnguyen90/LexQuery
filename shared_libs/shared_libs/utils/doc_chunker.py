import os
import re
import json
import logging
from glob import glob


from logging_setup import setup_logging
from shared_libs.utils.depreciated.load_config import load_config

# Configure logger
try:
    config = load_config('config/config.yaml')
except Exception as e:
    print(f"Failed to load configuration: {e}")
    

# Load the logger

setup_logging(config.get("processing").get("log_file"),level="INFO")    
logger = logging.getLogger(__name__)

# ----------------------------
# Configuration
# ----------------------------


# Define all possible hierarchical markers with their regex patterns
HIERARCHY_MARKERS = {
    'chương': re.compile(
        r'^\s*(?P<chương_marker>chương)\s+(?P<chương_number>[IVXLC]+|\d+)\s*[-.]?\s*(?P<chương_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'mục': re.compile(
        r'^\s*(?P<mục_marker>mục)\s+(?P<mục_number>\d+)\s*[-.]?\s*(?P<mục_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'điều': re.compile(
        r'^\s*(?P<điều_marker>điều)\s+(?P<điều_number>\d+)\s*[-.]?\s*(?P<điều_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'level2_rom': re.compile(
        r'^\s*(?P<level2_rom_marker>I{1,3}|IV|V|VI|VII|VIII|IX|X)\s*[-.]?\s*(?P<level2_rom_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'level3_num': re.compile(
        r'^\s*(?P<level3_num_marker>\d+)\s*[-.]?\s*(?P<level3_num_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'level4_alpha': re.compile(
        r'^\s*(?P<level4_alpha_marker>[a-zA-Z]{1,2})\s*[.)-]\s*(?P<level4_alpha_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
}

# Define the default hierarchy order
DEFAULT_HIERARCHY_ORDER = ['chương', 'mục', 'điều', 'level2_rom', 'level3_num', 'level4_alpha']

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
    Extracts text from a .docx file.
    
    Args:
        file_path (str): Path to the .docx file.
        
    Returns:
        str: Extracted text.
    """
    import docx
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        text = '\n'.join(full_text)
        logger.info(f"Extracted text from DOCX file: {file_path}")
        return text
    except Exception as e:
        logger.error(f"Error reading DOCX file {file_path}: {e}")
        return ""

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
    Detects which hierarchical markers are present in the document.
    
    Args:
        content (str): The raw text content of the document.
        
    Returns:
        list: List of hierarchical markers detected, ordered by their priority.
    """
    detected_markers = []
    for marker in DEFAULT_HIERARCHY_ORDER:
        pattern = HIERARCHY_MARKERS[marker]
        if pattern.search(content):
            detected_markers.append(marker)
            logger.debug(f"Detected hierarchical marker: {marker}")
    return detected_markers

def assign_hierarchy_levels(detected_markers):
    """
    Assigns hierarchical levels based on detected markers.
    
    Args:
        detected_markers (list): List of hierarchical markers detected.
        
    Returns:
        dict: Mapping of hierarchical markers to their assigned levels.
    """
    hierarchy_mapping = {}
    level = 1
    for marker in detected_markers:
        hierarchy_mapping[marker] = level
        logger.debug(f"Assigned level {level} to marker: {marker}")
        level += 1
    return hierarchy_mapping

def parse_hierarchy(content, hierarchy_mapping):
    """
    Parses the content into a hierarchical structure based on defined regex patterns and hierarchy mapping.
    
    Args:
        content (str): The raw text content of the document.
        hierarchy_mapping (dict): Mapping of hierarchical markers to their levels.
        
    Returns:
        list: Hierarchically structured sections and subsections.
    """
    sections = []
    stack = []  # Stack to keep track of hierarchy levels
    last_pos = 0

    # Create a combined regex pattern based on detected hierarchy markers
    combined_pattern_parts = []
    for marker in hierarchy_mapping:
        # Append the pattern as a named group
        combined_pattern_parts.append(f'(?P<{marker}>{HIERARCHY_MARKERS[marker].pattern})')
    # Combine all parts using OR
    combined_pattern = re.compile('|'.join(combined_pattern_parts), re.IGNORECASE | re.MULTILINE)

    for match in combined_pattern.finditer(content):
        start, end = match.span()
        matched_text = match.group().strip()
        level = None
        title = ""

        # Determine which group matched
        for marker in hierarchy_mapping:
            if match.group(marker):
                level = hierarchy_mapping[marker]
                match_details = HIERARCHY_MARKERS[marker].match(matched_text)
                if match_details:
                    # Extract the title based on the specific marker's title group
                    title_group_name = f"{marker}_title"
                    if title_group_name in match_details.groupdict():
                        title = match_details.group(title_group_name).strip() if match_details.group(title_group_name) else ""
                    # Update the title based on level-specific rules
                    if marker == 'level3_num':
                        title = f"Khoản {match_details.group('level3_num_marker') or matched_text}"
                    elif marker == 'level4_alpha':
                        title = f"Điểm {match_details.group('level4_alpha_marker') or matched_text}"
                break

        if level is None:
            continue  # Skip if no level matched

        logger.debug(f"Matched {marker.upper()} with level {level}: {matched_text} and title: {title}")

        # Extract the text between the last match and current match
        text = content[last_pos:start].strip()
        if text:
            # Otherwise, treat it as content
            if stack:
                current = stack[-1]
                if current['content']:
                    current['content'] += ' ' + text
                else:
                    current['content'] = text

        # Create a new section based on the detected level
        new_section = {
            'header': title,  # Swapping header and title as per user request
            'title': matched_text,
            'content': '',
            'subsections': []
        }

        # Assign any remaining content to the previous section
        if stack:
            current = stack[-1]
            remaining_text = content[last_pos:start].strip()
            if remaining_text:
                if current['content']:
                    current['content'] += ' ' + remaining_text
                else:
                    current['content'] = remaining_text

        # Adjust the stack based on the hierarchy level
        while stack and stack[-1]['level'] >= level:
            stack.pop()
        if stack:
            parent = stack[-1]
            parent['subsections'].append(new_section)
        else:
            sections.append(new_section)
        stack.append(new_section)
        new_section['level'] = level  # Assign level for future reference

        # Update the last position
        last_pos = end

    # Assign any remaining text after the last match
    if last_pos < len(content):
        remaining_text = content[last_pos:].strip()
        if remaining_text:
            if stack:
                current = stack[-1]
                if current['content']:
                    current['content'] += ' ' + remaining_text
                else:
                    current['content'] = remaining_text

    # Move title to content if no subsections exist
    for section in sections:
        def move_title_to_content(sec, parent_title=None, parent_header=None):
            if not sec['subsections'] and sec['title']:
                if not sec['content']:
                    sec['content'] = sec['title']
                    sec['title'] = ""
            for subsection in sec['subsections']:
                move_title_to_content(subsection, parent_title=sec['title'], parent_header=sec['header'])

        move_title_to_content(section)

    # Post-processing: Update titles if they are empty by trying to use titles from higher levels
    for section in sections:
        def update_empty_titles(sec, parent_title=None):
            if not sec['title']:
                sec['title'] = parent_title if parent_title else ""
            for subsection in sec['subsections']:
                update_empty_titles(subsection, sec['title'])

        update_empty_titles(section)

    # Remove 'level' keys from sections
    def remove_level(section):
        if 'level' in section:
            del section['level']
        for subsection in section.get('subsections', []):
            remove_level(subsection)

    for section in sections:
        remove_level(section)
        

    return sections

def create_structured_json(doc_number, doc_id, articles):
    """
    Creates a structured JSON object for a document.
    
    Args:
        doc_number (int): Document number.
        doc_id (str): Document ID.
        articles (list): List of articles with structured sections.
    
    Returns:
        dict: Structured JSON object.
    """
    return {
        "Doc_number": doc_number,
        "doc_id": doc_id,
        "articles": articles
    }

def parse_document(content, hierarchy_mapping):
    """
    Parses the entire document content based on the hierarchy mapping.
    
    Args:
        content (str): The raw text content of the document.
        hierarchy_mapping (dict): Mapping of hierarchical markers to their levels.
        
    Returns:
        list: List of structured articles.
    """
    structured_sections = parse_hierarchy(content, hierarchy_mapping)
    return structured_sections

def process_raw_file(file_path, output_json_path):
    """
    Processes a single raw text file and converts it into a structured JSON file.
    
    Args:
        file_path (str): Path to the raw text file.
        output_json_path (str): Path to save the structured JSON file.
    """
    try:
        # Extract text from the file
        raw_text = extract_text(file_path)
        if not raw_text:
            logger.warning(f"No text extracted from file: {file_path}")
            return

        # Detect hierarchical markers in the document
        detected_markers = detect_hierarchy(raw_text)
        if not detected_markers:
            logger.warning(f"No hierarchical markers detected in file: {file_path}")
            # Optionally, treat the entire document as a single section
            structured_sections = [{
                'header': '',
                'title': '',
                'content': raw_text,
                'subsections': []
            }]
        else:
            # Assign hierarchical levels based on detected markers
            hierarchy_mapping = assign_hierarchy_levels(detected_markers)
            # Parse the document based on the hierarchy mapping
            structured_sections = parse_document(raw_text, hierarchy_mapping)

        # Create structured JSON object
        doc_number = 1  # Assuming one document per file; adjust as needed
        document_json = create_structured_json(doc_number, "", structured_sections)
        documents = [document_json]

        # Write structured JSON to the output file
        with open(output_json_path, 'w', encoding='utf-8') as outfile:
            json.dump({"documents": documents}, outfile, ensure_ascii=False, indent=4)

        logger.info(f"Successfully processed file: {file_path} and saved to {output_json_path}")

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")

def process_section(section, indent_level=0):
    """
    Recursively processes a section or subsection to reconstruct text.
    
    Args:
        section (dict): The current section or subsection.
        indent_level (int): Current indentation level for formatting.
        
    Returns:
        str: The reconstructed text for this section.
    """
    indent = "    " * indent_level  # 4 spaces per indent level
    text = ""
    
    title = section.get("title", "")
    header = section.get("header", "")
    content = section.get("content", "")
    
    if title:
        text += f"{indent}{title}\n"
    
    if header and header not in title:
        text += f"{indent}{header}\n"
    
    if content:
        text += f"{indent}{content}\n"
    
    # Process subsections recursively
    subsections = section.get("subsections", [])
    for subsection in subsections:
        text += process_section(subsection, indent_level + 1)
    
    return text

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
        doc_number = document.get("Doc_number")
        doc_id = document.get("doc_id")
        
        if doc_number is not None:
            full_text += f"Document Number: {doc_number}\n"
        
        if doc_id:
            full_text += f"Doc ID: {doc_id}\n"
        
        articles = document.get("articles", [])
        for article in articles:
            full_text += process_section(article)
        
        # Optionally, add separators between documents
        full_text += "\n" + "-"*80 + "\n\n"
    
    return full_text


# ----------------------------
# Example Usage
# ----------------------------


if __name__ == "__main__":
    # Example file paths (Adjust these paths accordingly)
    raw_file = r'C:\Users\PC\git\Legal_QA_format\data\raw\ND-01-2020.docx'        # Replace with your raw file path
    output_json = r'C:\Users\PC\git\Legal_QA_format\data\raw\ND-01-2020.json'      # Replace with your desired JSON output path
    
    # Step 1: Convert raw file to structured JSON
    convert_raw_to_structured_json(raw_file, output_json)
    
    # Step 2: Reconstruct text from JSON
    full_text = reconstruct_text(output_json)
    
    # Step 3: Print or Save the Reconstructed Text
    if full_text:
        # Option 1: Print to Console
        # print(full_text)
        
        # Option 2: Write to a Text File (Uncomment if needed)
        reconstructed_text_path = r'C:\Users\PC\git\Legal_QA_format\data\raw\reconstructed_text.txt'
        with open(reconstructed_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"Reconstructed text has been written to '{reconstructed_text_path}'")
    else:
        print("No text was reconstructed.")