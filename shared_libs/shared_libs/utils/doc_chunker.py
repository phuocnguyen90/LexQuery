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
# Updated HIERARCHY_MARKERS
HIERARCHY_MARKERS = {
    'chương': re.compile(
        r'^\s*(?P<chương_marker>chương\s+[IVXLC]+)\s*[-.]?\s*(?P<chương_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'mục': re.compile(
        r'^\s*(?P<mục_marker>mục\s+[IVXLC]+|\d+)\s*[-.]?\s*(?P<mục_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'điều': re.compile(
        r'^\s*(?P<điều_marker>điều\s+\d+)\s*[-.]?\s*(?P<điều_title>.+)?$',
        re.IGNORECASE | re.MULTILINE
    ),
    'roman_numeral': re.compile(
        r'^\s*(?P<roman_numeral_marker>[IVXLC]+)\.\s*(?P<roman_numeral_title>.+)$',
        re.MULTILINE
    ),
    'number_dot': re.compile(
        r'^\s*(?P<number_dot_marker>\d+)\.\s*(?P<number_dot_title>.+)$',
        re.MULTILINE
    ),
    'level4_alpha': re.compile(
        r'^\s*(?P<level4_alpha_marker>[a-zA-Z]{1,2})\)\s*(?P<level4_alpha_title>.+)$',
        re.MULTILINE
    ),
}

# Define the default hierarchy order
DEFAULT_HIERARCHY_ORDER = ['chương', 'roman_numeral', 'mục', 'điều', 'number_dot', 'level4_alpha']


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
    sections = []
    stack = []  # Stack to keep track of hierarchy levels
    last_pos = 0

    # Create a combined regex pattern based on detected hierarchy markers
    combined_pattern_parts = []
    for marker in hierarchy_mapping:
        pattern = HIERARCHY_MARKERS[marker]
        combined_pattern_parts.append(f'(?P<{marker}>{pattern.pattern})')
    combined_pattern = re.compile('|'.join(combined_pattern_parts), re.IGNORECASE | re.MULTILINE)

    for match in combined_pattern.finditer(content):
        start, end = match.span()
        matched_text = match.group().strip()
        level = None
        title = ""
        header = ""

        # Determine which group matched
        for marker in hierarchy_mapping:
            if match.group(marker):
                level = hierarchy_mapping[marker]
                match_details = HIERARCHY_MARKERS[marker].match(matched_text)
                if match_details:
                    # Extract the title and header based on the specific marker's title group
                    title_group_name = f"{marker}_title"
                    marker_group_name = f"{marker}_marker"
                    if title_group_name in match_details.groupdict():
                        title = match_details.group(title_group_name).strip()
                    if marker_group_name in match_details.groupdict():
                        header = match_details.group(marker_group_name).strip()
                    else:
                        header = matched_text
                break

        if level is None:
            continue  # Skip if no level matched

        # Extract the text between the last match and current match
        text = content[last_pos:start].strip()
        if text:
            # Assign text to the content of the last section
            if stack:
                current = stack[-1]
                current['content'] += '\n' + text if current['content'] else text

        # Create a new section based on the detected level
        new_section = {
            'header': header,
            'title': title,
            'content': '',
            'subsections': []
        }

        # Adjust the stack based on the hierarchy level
        while stack and stack[-1]['level'] >= level:
            stack.pop()
        if stack:
            parent = stack[-1]
            parent['subsections'].append(new_section)
        else:
            sections.append(new_section)
        stack.append({'level': level, **new_section})

        # Update the last position
        last_pos = end

    # Assign any remaining text after the last match
    if last_pos < len(content):
        remaining_text = content[last_pos:].strip()
        if remaining_text and stack:
            current = stack[-1]
            current['content'] += '\n' + remaining_text if current['content'] else remaining_text

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
        "doc_number": doc_number,
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
        # Extract file name from the file path
        doc_filename = os.path.basename(file_path)

        # Extract text from the file
        raw_text = extract_text(file_path)
        if not raw_text:
            logger.warning(f"No text extracted from file: {file_path}")
            return

        # Split the text into elements
        elements = raw_text.split("\n")
        doc_id = ""
        # Increase the range if necessary to capture the doc_id
        for element in elements[:30]:  # Adjusted range as needed
            element = element.strip()
            # Skip table tags
            if element in ("<table>", "</table>", "<tr>", "</tr>"):
                continue
            # If element is a table cell
            if element.startswith("<td>") and element.endswith("</td>"):
                # Extract cell content
                element_text = element[4:-5].strip()
            else:
                element_text = element

            # Updated regex pattern to match "Số:" and "Luật số:"
            match = re.search(r"(?:Số|Luật số)[:\s]*([^\s,;]+)", element_text)
            if match:
                doc_id = match.group(1).strip()
                break

        # Detect hierarchical markers in the document
        detected_markers = detect_hierarchy(raw_text)
        if not detected_markers:
            logger.warning(f"No hierarchical markers detected in file: {file_path}")
            structured_sections = [{
                'header': '',
                'title': '',
                'content': raw_text,
                'subsections': []
            }]
        else:
            hierarchy_mapping = assign_hierarchy_levels(detected_markers)
            structured_sections = parse_document(raw_text, hierarchy_mapping)

        # Create structured JSON object
        doc_number = 1  # Assuming one document per file
        document_json = create_structured_json(doc_number, doc_id, structured_sections)
        documents = [document_json]

        # Write structured JSON to the output file
        with open(output_json_path, 'w', encoding='utf-8') as outfile:
            json.dump({
                "doc_filename": doc_filename,
                "documents": documents
            }, outfile, ensure_ascii=False, indent=4)

        logger.info(f"Successfully processed file: {file_path} and saved to {output_json_path}")

    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}")

def process_section(section, indent_level=0, parent_headers=None):
    """
    Recursively processes a section or subsection to reconstruct text,
    including full hierarchy headers.

    Args:
        section (dict): The current section or subsection.
        indent_level (int): Current indentation level for formatting.
        parent_headers (list): List of headers from parent sections.

    Returns:
        str: The reconstructed text for this section.
    """
    if parent_headers is None:
        parent_headers = []

    indent = "    " * indent_level
    text = ""

    header = section.get("header", "")
    title = section.get("title", "")
    content = section.get("content", "")

    # Update the list of parent headers
    current_headers = parent_headers + [header] if header else parent_headers

    # Construct the full reference
    full_reference = ', '.join(filter(None, reversed(current_headers)))

    # Add the full reference to the text
    if full_reference:
        text += f"{indent}{full_reference}\n"

    # Add the title if it exists
    if title:
        text += f"{indent}{title}\n"

    # Add the content
    if content:
        text += f"{indent}{content}\n"

    # Process subsections recursively
    subsections = section.get("subsections", [])
    for subsection in subsections:
        text += process_section(subsection, indent_level + 1, current_headers)

    return text


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

        articles = document.get("articles", [])
        for article in articles:
            # Pass the doc_id as part of the parent headers
            full_text += process_section(article, indent_level=0, parent_headers=[doc_id])

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


# ----------------------------
# Example Usage
# ----------------------------


if __name__ == "__main__":
    # Example file paths (Adjust these paths accordingly)
    raw_file = r'format_service\src\data\raw\1. DOANH NGHIỆP\1.1.1 79_2010_BTC_converted.docx'        # Replace with your raw file path
    output_json = r'format_service\src\data\raw\1.1.1 79_2010_BTC_converted.json'      # Replace with your desired JSON output path
    
    # Step 1: Convert raw file to structured JSON
    convert_raw_to_structured_json(raw_file, output_json)
    
    # Step 2: Reconstruct text from JSON
    full_text = reconstruct_text(output_json)
    
    # Step 3: Print or Save the Reconstructed Text
    if full_text:
        # Option 1: Print to Console
        # print(full_text)
        
        # Option 2: Write to a Text File (Uncomment if needed)
        reconstructed_text_path = r'format_service\src\data\raw\1. DOANH NGHIỆP\1.1.1 79_2010_BTC_converted.txt'
        with open(reconstructed_text_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"Reconstructed text has been written to '{reconstructed_text_path}'")
    else:
        print("No text was reconstructed.")