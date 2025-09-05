import pandas as pd
import re
from typing import List, Tuple, Dict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentMatcher:
    def __init__(self, csv_path: str):
        """
        Initialize the DocumentMatcher with the path to the CSV file containing document data.

        :param csv_path: Path to the CSV file containing documents.
        """
        try:
            self.documents = self.load_documents(csv_path)
            logger.info("Successfully loaded document database.")
            # Separate documents by type for Luật, Bộ luật, Pháp lệnh
            self.luat_documents = [doc for doc in self.documents if doc['Full Name'].startswith(('Luật', 'Bộ luật', 'Pháp lệnh'))]
            logger.debug(f"Loaded {len(self.luat_documents)} Luật/Bộ luật/Pháp lệnh documents.")
            # Create a mapping for issuers from Thông tư documents
            
        except Exception as e:
            logger.error(f"Cannot load document database with error: {e}")
            raise
    def preprocess_database(self):
        """
        Preprocess the document database to facilitate partial matching.
        """
        self.partial_mapping = {}
        # Define abbreviations for document types
        self.abbreviations = {
            "Nghị định": "NĐ",
            "Thông tư": "TT",
            "Thông tư liên tịch": "TTLT",
            "Pháp lệnh": "PL",
            "Nghị quyết":"NQ"
            # Add more abbreviations as needed
        }

        # Create a mapping from (Document Type, Year) to full mentions
        for doc in self.documents:
            full_name = doc['Full Name']
            doc_id = doc['Document_ID']
            issued_date = doc['Issued Date']
            # Extract document type and year from full_name
            match = re.match(r"(Luật|Bộ luật|Pháp lệnh|Nghị định|Thông tư(?: liên tịch)?|Nghị quyết|Quyết định)\s+(\d{1,3}/\d{4})", full_name, re.UNICODE)
            if match:
                doc_type = match.group(1)
                doc_year = match.group(2).split('/')[1]  # Extract year part
                key = (doc_type, doc_year)
                if key not in self.partial_mapping:
                    self.partial_mapping[key] = []
                self.partial_mapping[key].append(full_name)
        logger.debug(f"Preprocessed partial mapping: {self.partial_mapping}")


    def load_documents(self, csv_path: str) -> List[Dict[str, str]]:
        """ 
        Load documents from a CSV file into a list of dictionaries.
        
        :param csv_path: Path to the CSV file containing documents.
        :return: List of document dictionaries.
        """
        try:
            df = pd.read_csv(csv_path)
            logger.debug(f"Loaded {len(df)} documents from {csv_path}.")
            return df.to_dict(orient='records')
        except Exception as e:
            logger.error(f"Error loading documents from {csv_path}: {e}")
            raise

    def extract_document_mentions(self, text: str) -> List[str]:
        """ 
        Extract document mentions from the text using regex and additional logic.
        Identifies various types of legal documents with their IDs based on the specified rules.
        
        :param text: The text content to search for document mentions.
        :return: List of extracted document mentions.
        """
        mentions = set()

        # Define the document types
        first_category_keywords = {"Luật", "Bộ luật", "Pháp lệnh"}
        second_category_keywords = {"Nghị định", "Thông tư", "Nghị quyết", "Quyết định"}

        # 1. Use regex to find all mentions
        # Adjusted regex to capture the entire mention including the ID
        # The pattern matches the document type followed by a space and then the ID
        # IDs can have slashes and hyphens, like 77/2012/TT-BTC or 92/2012/NĐ-CP
        # Use non-capturing group for the document type
        pattern = r"(?:Luật|Bộ luật|Pháp lệnh|Nghị định|Thông tư(?: liên tịch)?|Nghị quyết|Quyết định) \d{1,3}/\d{4}(?:/[\w\-]+)?"
        regex_matches = re.finditer(pattern, text, re.UNICODE)


        for match in regex_matches:
            full_mention = match.group(0)
            mentions.add(full_mention)
            logger.info(f"Regex found mention: {full_mention}")

        # 2. Split the text into words for further extraction
        words = text.split()
        logger.debug(f"Text split into words: {words}")

        # Iterate through words to find mentions based on keyword categories
        for i, word in enumerate(words):
            # Check for first category keywords
            if word in first_category_keywords:
                # Capture up to 5 words after the keyword
                following_words = words[i+1:i+6]  # 5 words after the keyword
                mention_text = " ".join(following_words)
                logger.debug(f"First category keyword '{word}' found. Following words: {following_words}")
                # Look for parts with '/' or '-' to indicate IDs
                id_pattern = r"\d{1,3}/\d{4}(?:/[A-Za-z\-]+)?"
                id_match = re.search(id_pattern, mention_text)
                if id_match:
                    extracted_id = id_match.group(0)
                    full_mention = f"{word} {extracted_id}"
                    mentions.add(full_mention)
                    logger.info(f"Extracted mention from first category: {full_mention}")

            # Check for second category keywords
            elif word in second_category_keywords:
                # Capture up to 4 words after the keyword
                following_words = words[i+1:i+5]  # 4 words after the keyword
                mention_text = " ".join(following_words)
                logger.debug(f"Second category keyword '{word}' found. Following words: {following_words}")
                # Look for parts with '/' or '-' to indicate IDs
                id_pattern = r"\d{1,3}/\d{4}(?:/[A-Za-z\-]+)?"
                id_match = re.search(id_pattern, mention_text)
                if id_match:
                    extracted_id = id_match.group(0)
                    full_mention = f"{word} {extracted_id}"
                    mentions.add(full_mention)
                    logger.info(f"Extracted mention from second category: {full_mention}")

        
            # 3. Handle partial mentions if no full mentions are found
            if not mentions:
                logger.debug("No full mentions found. Attempting to extract partial mentions.")
                partial_pattern = r"(Luật|Bộ luật|Pháp lệnh|Nghị định|Thông tư(?: liên tịch)?|Nghị quyết|Quyết định)\s+\d{1,3}/\d{4}"
                partial_matches = re.finditer(partial_pattern, text, re.UNICODE)
                for match in partial_matches:
                    doc_type = match.group(1)
                    partial_id = match.group(2)  # e.g., "92/2012"
                    key = (doc_type, partial_id.split('/')[1])  # (Document Type, Year)
                    logger.debug(f"Partial mention found: {match.group(0)}. Looking up in partial mapping with key: {key}")
                    if key in self.partial_mapping:
                        # If multiple full mentions match, add all
                        for full_name in self.partial_mapping[key]:
                            mentions.add(full_name)
                            logger.debug(f"Reconstructed full mention from partial: {full_name}")
                    else:
                        logger.debug(f"No matching full mention found for partial key: {key}")

        unique_mentions = list(mentions)
        logger.info(f"Unique document mentions after processing: {unique_mentions}")
        return unique_mentions

    def extract_issue_year_from_mention(self, mention: str) -> str:
        """
        Extract the year from a document mention.
        
        :param mention: The document mention string.
        :return: The extracted year as a string, or None if not found.
        """
        year_pattern = r"/(\d{4})"
        match = re.search(year_pattern, mention)
        year = match.group(1) if match else None
        logger.debug(f"Extracted year '{year}' from mention '{mention}'.")
        return year

    def calculate_matching_score(self, doc: Dict[str, str], mention: str, issue_year: str) -> float:
        """
        Calculate the matching score for a document based on title and issue year.

        :param doc: The document dictionary from the database.
        :param mention: The extracted document mention from the text.
        :param issue_year: The extracted year from the mention.
        :return: The total matching score as a float.
        """
        title = doc['Full Name']  
        doc_issue_year = str(doc.get('issue_year'))  # Ensure it's a string for comparison

        # Calculate title matching
        title_match = mention.lower() in title.lower()
        title_score = 0.7 if title_match else 0.0  # 70% if title matches

        # Calculate issue year matching
        date_score = 0.3 if issue_year and issue_year == doc_issue_year else 0.0  # 30% if date matches

        # Total score calculation
        total_score = title_score + date_score

        logger.debug(f"Calculating score for mention '{mention}': Title Score = {title_score}, Date Score = {date_score}, Total Score = {total_score}")
        return total_score

    def find_best_matching_document(self, text: str) -> Tuple[str, str, float]:
        """
        Find the best matching document based on text input.

        :param text: The text content to search for document mentions.
        :return: A tuple containing the best document ID, file name, and the matching score.
        """
        mentions = self.extract_document_mentions(text)
        logger.debug(f"Mentions found: {mentions}")

        best_score = 0.0
        best_doc_id = None
        best_file_name = None

        for mention in mentions:
            issue_year = self.extract_issue_year_from_mention(mention)
            for doc in self.documents:
                score = self.calculate_matching_score(doc, mention, issue_year)
                logger.debug(f"Score for document '{doc['Document_ID']}': {score}")
                if score > best_score:
                    best_score = score
                    best_doc_id = doc['Document_ID']  
                    best_file_name = doc['Filename']   
                    logger.debug(f"New best match: ID = {best_doc_id}, Name = {best_file_name}, Score = {best_score:.2f}")

        logger.info(f"Best matching document: ID = {best_doc_id}, Name = {best_file_name}, Score = {best_score:.2f}")
        return best_doc_id, best_file_name, best_score

    
# testing
import json
matcher=DocumentMatcher("src\data\doc_db.csv")# Define the test record as a JSON string
test_record = """{
    "record_id": "QA_0D20CLOUDD",
    "document_id": "N/A",
    "title": "Thủ tục cấp lại Giấy phép sản xuất rượu thủ công",
    "content": "Căn cứ pháp lý:\\nThông tư 77/2012;\\nNghị định 92/2012;\\nThông tư 60/2019.\\n\\nI/ Trình tự thực hiện\\nBước 1:Các tổ chức, cá nhân tự chuẩn bị đầy đủ hồ sơ theo quy định của pháp luật và nộp hồ sơ tại Bộ phận tiếp nhận và trả kết quả của Ủy ban nhân dân cấp xã.\\nBước 2: Công chức tiếp nhận và kiểm tra hồ sơ.\\nBước 3: Công chức tiếp nhận hồ sơ chuyển hồ sơ đến cán bộ phụ trách để thẩm định.\\nBước 4: Đến ngày hẹn ghi trong Giấy tiếp nhận hồ sơ và hẹn trả kết quả, cá nhân đến Bộ phận tiếp nhận và trả kết quả của Ủy ban nhân dân cấp xã, ký nhận kết quả thủ tục hành chính và nộp lại Giấy tiếp nhận hồ sơ và hẹn trả kết quả.\\n\\nII/ Cách thức thực hiện: Gửi hồ sơ qua đường bưu điện hoặc nộp trực tiếp tại Bộ phận tiếp nhận và trả kết quả giải quyết thủ tục hành chính của UBND cấp xã.\\n\\nIII/ Thành phần hồ sơ: (01 bộ)\\n– Trường hợp cấp lại do hết thời hạn hiệu lực: + Giấy đăng ký sản xuất rượu thủ công để bán cho các doanh nghiệp có Giấy phép sản xuất rượu để chế biến lại; + Bản sao Hợp đồng mua bán giữa tổ chức, cá nhân đề nghị đăng ký sản xuất rượu thủ công và doanh nghiệp có Giấy phép sản xuất rượu để chế biến lại rượu.\\n– Trường hợp Giấy xác nhận đăng ký sản xuất rượu thủ công để bán cho doanh nghiệp có Giấy phép sản xuất rượu để chế biến lại bị mất, bị tiêu hủy toàn bộ hoặc một phần, bị rách, nát hoặc bị cháy : – Giấy đăng ký cấp lại. – Bản gốc hoặc bản sao Giấy xác nhận đăng ký sản xuất rượu thủ công để bán cho doanh nghiệp có Giấy phép sản xuất rượu để chế biến lại.\\n\\nIV/ Thời hạn giải quyết\\nTrong thời hạn 10 (mười) ngày làm việc, kể từ ngày nhận đủ hồ sơ hợp lệ theo quy định. Ủy ban nhân dân cấp Xã xem xét và cấp lại Giấy xác nhận đăng ký sản xuất rượu thủ công để bán cho doanh nghiệp có Giấy phép sản xuất rượu để chế biến lại.\\n\\nV/ Cơ quan có thẩm quyền: Ủy ban nhân dân cấp xã\\nVI/ Phí, lệ phí:\\nLệ phí cấp lại Giấy xác nhận đăng ký sản xuất rượu thủ công để bán cho doanh nghiệp có Giấy phép sản xuất rượu để chế biến lại.",
    "chunk_id": "N/A",
    "hierarchy_level": 1,
    "categories": ["Thủ Tục Hành Chính"],
    "relationships": [],
    "published_date": "June 1, 2020",
    "source": null,
    "processing_timestamp": "2024-09-29T13:56:49.615124",
    "validation_status": false,
    "language": "vi",
    "summary": ""
}"""
test_content=json.loads(test_record)
content_text = test_content["content"]

document_id, file_name, score = matcher.find_best_matching_document(content_text)
# Print the results
print(f"Document ID: {document_id}, File Name: {file_name}, Score: {score:.2f}")