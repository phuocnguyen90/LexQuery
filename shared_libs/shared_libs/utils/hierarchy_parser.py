
import re

# Revised HIERARCHY_MARKERS
import re

# Revised HIERARCHY_MARKERS with stricter Roman numeral handling
HIERARCHY_MARKERS = {
    'chapter': re.compile(
        r'^\s*(Chương\s+(?P<chapter_value>\w+))\s*[-.]?\s*(?P<chapter_title_chap>.*)$',
        re.IGNORECASE | re.MULTILINE | re.UNICODE
    ),
    'roman_chapter': re.compile(
        r'^\s*(?P<roman_numeral_chap>(?:[IVXLCDM]{2,}|[IVXLCDM]\b))\s*[-.]?\s*(?P<chapter_title_roman>.+)$',
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
# Define the default hierarchy order
DEFAULT_HIERARCHY_ORDER = ['chapter', 'roman_chapter', 'article', 'clause', 'point']



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
                    if marker == 'chapter':
                        marker_text = match_details.group('chapter_value').strip()
                        header = f"Chương {marker_text}"
                        marker_value = marker_text
                        title_text = match_details.group('chapter_title_chap')
                    elif marker == 'roman_chapter':
                        marker_text = match_details.group('roman_numeral_chap').strip()
                        header = f"Phần {marker_text}"
                        marker_value = marker_text
                        title_text = match_details.group('chapter_title_roman')
                    elif marker == 'article':
                        marker_text = match_details.group('article_marker').strip()
                        marker_value = match_details.group('article_value').strip()
                        header = f"Điều {marker_value}"
                        title_text = match_details.group('article_title')
                    elif marker == 'clause':
                        marker_text = match_details.group('clause_marker').strip()
                        marker_value = match_details.group('clause_value').strip()
                        header = f"Khoản {marker_value}"
                        title_text = match_details.group('clause_title')
                    elif marker == 'point':
                        marker_text = match_details.group('point_marker').strip()
                        marker_value = match_details.group('point_value').strip()
                        header = f"Điểm {marker_value}"
                        title_text = match_details.group('point_title')

                    # Handle title
                    if title_text:
                        title = title_text.strip()
                    else:
                        title = ""

                    # If title is empty, treat the entire line as content
                    if not title:
                        content_line = matched_text.strip()
                    else:
                        content_line = ""

                    marker_type = marker

                    # Build the marker_part for this section
                    if marker_type in ['chapter', 'roman_chapter']:
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

        # Adjust the stack to maintain correct hierarchy
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

            # If current marker is `clause` but there's no `article` in the stack, attach to `chapter`
            if marker_type == 'clause':
                if parent_section['header'].startswith("Chương") or parent_section['header'].startswith("Phần"):
                    # There is no `article` in the stack, so add `clause` directly to `chapter`
                    parent_section['subsections'].append(new_section)
                else:
                    # Otherwise, add it to the `article`
                    parent_section['subsections'].append(new_section)

            # If current marker is `point` but no `clause` in stack, attach it directly to `article` or `chapter`
            elif marker_type == 'point':
                if parent_section['header'].startswith("Khoản"):
                    # If the current parent is `clause`, add the point to it
                    parent_section['subsections'].append(new_section)
                elif parent_section['header'].startswith("Điều"):
                    # Otherwise, add it directly to `article`
                    parent_section['subsections'].append(new_section)
                elif parent_section['header'].startswith("Chương") or parent_section['header'].startswith("Phần"):
                    # If no clause or article, attach to `chapter`
                    parent_section['subsections'].append(new_section)
            else:
                # Otherwise, for `chapter`, `article`, or valid parent-child relations, add normally
                parent_section['subsections'].append(new_section)
        else:
            # Top-level sections (e.g., chapter)
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