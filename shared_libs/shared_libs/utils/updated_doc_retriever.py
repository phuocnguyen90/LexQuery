# WIP dynamic weighting for doc match
import os
import logging
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import underthesea
from underthesea import word_tokenize 
import pickle
from typing import List, Tuple, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compute_tfidf_similarity(query, documents, stop_words=None):
    vectorizer = TfidfVectorizer(stop_words=stop_words).fit(documents)
    query_vec = vectorizer.transform([query])
    doc_vecs = vectorizer.transform(documents)
    sims = cosine_similarity(query_vec, doc_vecs).flatten()
    return sims

def compute_similarity(query_text, document_text, stop_words=None):
    vectorizer = TfidfVectorizer(stop_words=stop_words).fit([query_text, document_text])
    vectors = vectorizer.transform([query_text, document_text])
    similarity = cosine_similarity(vectors[0], vectors[1])[0][0]
    return similarity

class CombinedDocumentSearch:
    def __init__(self, csv_path: str, token_db_path: str = 'src/data/token_db.pkl'):
        """
        Initialize the CombinedDocumentSearch with paths to the CSV and token database.

        :param csv_path: Path to the CSV file containing documents.
        :param token_db_path: Path to the token database pickle file.
        """
        self.csv_path = csv_path
        self.token_db_path = token_db_path
        self.stopwords = {
            'quy định', 'ban hành',  
            'và', 'về', 'đối với', 'của', 'do', 'các',
            'trong',      
            'thuộc', '2020' 
        }
        self.documents = self.load_documents()
        self.token_db = None
        self._load_or_create_token_database()

        self.equivalent_document_types = {
            'luật': ['luật', 'bộ luật', 'pháp lệnh'],
            'bộ luật': ['luật', 'bộ luật', 'pháp lệnh'],
            'pháp lệnh': ['luật', 'bộ luật', 'pháp lệnh'],
            # Add other mappings if necessary
        }

        # Initialize issuer mapping
        self.issuer_mapping = {
            'bộ công thương': 'bct',
            'bộ nội vụ': 'bnv',
            'bộ giáo dục': 'bgddt',
            'bộ tài chính': 'btc',
            'bộ quốc phòng': 'bqp',
            'bộ công an': 'bca',
            'bộ y tế': 'byt',
            'bộ thông tin': 'btttt',
            'bộ ngoại giao': 'bng',
            'bộ tư pháp': 'btp',
            'bộ kế hoạch': 'bkhdt',
            'bộ nông nghiệp': 'bnnptnt',
            'bộ giao thông': 'bgtvt',
            'bộ xây dựng': 'bxd',
            'bộ tài nguyên': 'btnmt',
            'bộ lao động': 'bldtbxh',
            'bộ văn hóa': 'bvhttdl',
            'bộ khoa học': 'bkhcn',
            'ngân hàng nhà nước': 'nhnn'

            # Add more mappings as necessary
        }

    def load_documents(self) -> pd.DataFrame:
        """
        Load documents from a CSV file into a DataFrame.

        :return: DataFrame of documents.
        """
        try:
            df = pd.read_csv(self.csv_path)
            logger.info(f"Loaded {len(df)} documents from {self.csv_path}.")

            # Normalize text columns: lowercase and strip whitespace
            text_columns = ['document_number', 'document_type', 'issuer_body', 'Full Name', 'Document_ID']
            for col in text_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.lower().str.strip()
                else:
                    logger.warning(f"Column '{col}' not found in DataFrame.")

            return df
        except Exception as e:
            logger.error(f"Error loading documents from {self.csv_path}: {e}")
            raise

    def _load_or_create_token_database(self):
        """
        Load or create the token database using TF-IDF.
        """
        if os.path.exists(self.token_db_path):
            logger.info("Loading token database from pickle file.")
            with open(self.token_db_path, 'rb') as f:
                self.token_db = pickle.load(f)
        else:
            logger.info("Creating new token database from document database.")
            documents = self.documents['Full Name'].tolist()
            self.token_db = self.create_token_database(documents, apply_tfidf=True)
            with open(self.token_db_path, 'wb') as f:
                pickle.dump(self.token_db, f)
            logger.info("Token database created and saved.")

    def create_token_database(self, documents, apply_tfidf=False):
        """
        Create a token frequency database from documents with optional TF-IDF weighting.
        
        :param documents: List of document titles.
        :param apply_tfidf: Whether to apply TF-IDF weighting.
        :return: Token frequency or TF-IDF scores dictionary.
        """
        # Tokenize and remove stopwords
        tokenized_docs = []
        for doc in documents:
            tokens = word_tokenize(doc.lower())
            filtered_tokens = [token for token in tokens if token not in self.stopwords]
            tokenized_docs.append(' '.join(filtered_tokens))
        
        if apply_tfidf:
            vectorizer = TfidfVectorizer(stop_words=list(self.stopwords))  # Convert set to list
            tfidf_matrix = vectorizer.fit_transform(tokenized_docs)
            feature_names = vectorizer.get_feature_names_out()
            
            tfidf_scores = {}
            for idx, token in enumerate(feature_names):
                tfidf_scores[token] = tfidf_matrix[:, idx].sum()
            return tfidf_scores
        else:
            token_freq = defaultdict(int)
            for doc in tokenized_docs:
                tokens = doc.split()
                for token in tokens:
                    token_freq[token] += 1
            return dict(token_freq)

    def search(self, query: str, top_n: int = 1, fuzzy: bool = True, cutoff: float = 0.5) -> Dict[str, List[Tuple[str, str, float]]]:
        matches = defaultdict(list)
        # Extract mentions along with their detailed information
        extracted_mentions = self.extract_document_mentions(query)

        for mention_dict in extracted_mentions:
            mention = mention_dict['mention']
            document_type = mention_dict['document_type']
            document_number = mention_dict['document_number']  
            issue_year = mention_dict['issue_year']
            issuer_body = mention_dict['issuer_body']
            extra_info = mention_dict['extra_info']

            mention_matches = self.match_documents(
                mention, 
                document_type,
                document_number,     
                issue_year,
                issuer_body,
                extra_info,
                top_n=top_n,
                fuzzy=fuzzy,
                cutoff=cutoff
            )
            for key, value in mention_matches.items():
                matches[key].extend(value)

        # Sort and trim matches
        for mention, match_list in matches.items():
            sorted_match_list = sorted(match_list, key=lambda x: x[2], reverse=True)
            matches[mention] = sorted_match_list[:top_n]
            logger.info(f"Top {top_n} matches for mention '{mention}': {matches[mention]}")

        return matches

    def extract_document_mentions(self, text: str) -> List[Dict[str, str]]:
        mentions = []
        # Split text into sentences
        sentences = underthesea.sent_tokenize(text)
        logger.debug(f"Sentences after tokenization: {sentences}")

        # Define mention keywords
        first_group_keywords = ['luật', 'bộ luật', 'pháp lệnh']
        other_keywords = ['nghị định', 'thông tư', 'nghị quyết', 'quyết định']
        all_keywords = first_group_keywords + other_keywords

        # Preprocess keywords to handle multi-word phrases
        keyword_max_length = max(len(k.split()) for k in all_keywords)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # Tokenize the sentence using whitespace
            tokens = sentence.split()
            logger.debug(f"Tokens: {tokens}")
            i = 0
            while i < len(tokens):
                # Function to match keywords considering multi-word phrases
                def get_matching_keyword(tokens, i, keywords):
                    for length in range(keyword_max_length, 0, -1):
                        if i + length <= len(tokens):
                            phrase = ' '.join(tokens[i:i+length]).lower()
                            if phrase in keywords:
                                return phrase, length
                    return None, 0

                # Try to match any keyword starting at position i
                keyword, keyword_length = get_matching_keyword(tokens, i, all_keywords)
                if keyword:
                    # Start building the mention
                    mention_tokens = tokens[i:i+keyword_length]
                    count = 0
                    j = i + keyword_length
                    # Take at least the next 3 tokens, unless an exception applies
                    while j < len(tokens) and count < 3:
                        next_keyword, _ = get_matching_keyword(tokens, j, all_keywords)
                        if next_keyword:
                            break
                        mention_tokens.append(tokens[j])
                        count += 1
                        j += 1
                    # After initial tokens, collect up to 3 tokens for extra_info
                    extra_info_count = 0
                    while j < len(tokens) and extra_info_count < 3:
                        next_keyword, _ = get_matching_keyword(tokens, j, all_keywords)
                        if next_keyword:
                            break
                        mention_tokens.append(tokens[j])
                        extra_info_count += 1
                        j += 1
                    # Create the mention text
                    mention_text = ' '.join(mention_tokens)
                    # Extract extra_info (tokens after the document_type)
                    extra_info = ' '.join(mention_tokens[keyword_length:])
                    # Try to extract issue_year from tokens
                    issue_year = ''
                    for t in tokens[i:j]:
                        if re.match(r'\b\d{4}\b', t):
                            issue_year = t
                            break
                    # Remove issue_year from extra_info if present
                    if issue_year and issue_year in extra_info:
                        extra_info = extra_info.replace(issue_year, '').strip()
                    mentions.append({
                        'mention': mention_text,
                        'document_type': keyword,
                        'document_number': '',
                        'issue_year': issue_year,
                        'issuer_body': '',
                        'extra_info': extra_info
                    })
                    logger.debug(f"Extracted mention: {mentions[-1]}")
                    i = j  # Continue from where we left off
                else:
                    i += 1  # Move to the next token
            # End of sentence processing
        logger.info(f"Extracted mentions with detailed info: {mentions}")
        return mentions

    def match_documents(
        self, 
        mention: str, 
        document_type: str,
        document_number: str,
        issue_year: str,
        issuer_body: str,
        extra_info: str,
        top_n: int = 2,
        fuzzy: bool = False,
        cutoff: float = 0.5  # Adjust as needed
    ) -> Dict[str, List[Tuple[str, str, float]]]:
        matches = defaultdict(list)

        # Assign base confidence scores
        base_confidences = {
            'document_type': 1.0 if document_type else 0.0,
            'document_number': 1.0 if document_number else 0.0,
            'issue_year': 1.0 if issue_year else 0.0,
            'issuer_body': 1.0 if issuer_body else 0.0,
            'extra_info': 1.0 if extra_info else 0.0
        }

        # Assign reliability factors
        reliability_factors = {
            'document_type': 0.8,
            'document_number': 0.9,
            'issue_year': 0.7,
            'issuer_body': 0.8,
            'extra_info': 0.6
        }

        # Calculate confidence scores
        confidence_scores = {}
        total_confidence = 0.0
        for prop in base_confidences:
            confidence = base_confidences[prop] * reliability_factors[prop]
            confidence_scores[prop] = confidence
            total_confidence += confidence

        # Normalize weights
        dynamic_weights = {}
        for prop in confidence_scores:
            if total_confidence > 0:
                dynamic_weights[prop] = confidence_scores[prop] / total_confidence
            else:
                dynamic_weights[prop] = 0.0

        # Build initial conditions based on available properties
        combined_condition = pd.Series(True, index=self.documents.index)
        for prop in ['document_type', 'document_number', 'issue_year', 'issuer_body']:
            value = locals()[prop]
            if value:
                if prop == 'document_type':
                    # Handle equivalent document types
                    equivalent_types = self.equivalent_document_types.get(value.lower(), [value.lower()])
                    condition = self.documents['document_type'].str.lower().isin(equivalent_types)
                else:
                    condition = self.documents[prop].str.lower() == value.lower()
                combined_condition &= condition

        # Apply conditions to get potential matches
        potential_matches = self.documents[combined_condition]
        logger.debug(f"Potential matches based on provided properties: {len(potential_matches)}")

        # Calculate match scores for potential matches
        for idx, doc in potential_matches.iterrows():
            match_score = 0.0

            # Check property matches
            for prop in ['document_type', 'document_number', 'issue_year', 'issuer_body']:
                value = locals()[prop]
                if value:
                    if prop == 'document_type':
                        match = doc['document_type'].lower() in self.equivalent_document_types.get(value.lower(), [value.lower()])
                    else:
                        match = doc[prop].lower() == value.lower()
                    if match:
                        match_score += dynamic_weights[prop]
                    else:
                        # Penalize mismatches
                        match_score -= dynamic_weights[prop]

            # Compute similarity for extra_info
            if extra_info:
                similarity = compute_similarity(extra_info.lower(), doc['Full Name'].lower(), stop_words=list(self.stopwords))  # Convert set to list
                match_score += dynamic_weights['extra_info'] * similarity

            # Add match to results if score exceeds cutoff
            if match_score >= cutoff:
                matches[mention].append((doc['Full Name'], doc['Document_ID'], match_score))

        # Sort matches by score
        matches[mention] = sorted(matches[mention], key=lambda x: x[2], reverse=True)[:top_n]
        if matches[mention]:
            logger.info(f"Found matches for mention '{mention}' with dynamic scoring.")
        else:
            logger.info(f"No matches found for mention '{mention}'.")

        return matches

    def calculate_matching_score(self, doc: pd.Series, mention: str) -> float:
        """
        Calculate the matching score for a document based on title similarity, issue year, and other criteria.

        :param doc: The document row from the DataFrame.
        :param mention: The mention extracted from the query.
        :return: The calculated matching score.
        """
        # This method is now integrated into match_documents and can be removed or repurposed
        pass  # Placeholder if needed for future enhancements

    def extract_issue_year_from_mention(self, mention: str) -> str:
        """
        Extract the year from a document mention. For multiple mentions, match the found year
        with the nearest mention to the left of the year.

        :param mention: The document mention string.
        :return: The extracted year as a string, or None if not found.
        """
        year_pattern = r"/(\d{4})"
        matches = list(re.finditer(year_pattern, mention))
        if not matches:
            return None
        
        # If multiple years are found, match the year to the nearest mention on the left
        mention_positions = [m.start() for m in re.finditer(r"(?:Luật|Bộ luật|Pháp lệnh|Nghị định|Thông tư(?: liên tịch)?|Nghị quyết|Quyết định) \d{1,3}/\d{4}(?:/[\w\-]+)?", mention)]
        extracted_year = None
        for match in matches:
            year_pos = match.start()
            nearest_mention_pos = max((pos for pos in mention_positions if pos < year_pos), default=None)
            if nearest_mention_pos is not None:
                extracted_year = match.group(1)
                break
        
        return extracted_year

    def analyze_token_database(self):
        """
        Analyze the token database to find common tokens to exclude.
        """
        # Ensure the token database is loaded
        self._load_or_create_token_database()

        # Assuming self.token_db is a dictionary {token: score}
        # Sort tokens by their TF-IDF scores in descending order
        sorted_tokens = sorted(self.token_db.items(), key=lambda item: item[1], reverse=True)

        # Print or log the top N tokens
        top_n = 100  # Adjust N as needed
        logger.info(f"Top {top_n} tokens by TF-IDF scores:")
        for token, score in sorted_tokens[:top_n]:
            print(f"{token}: {score}")

# Example usage
if __name__ == "__main__":
    # Use raw string for Windows paths or forward slashes
    searcher = CombinedDocumentSearch(r"src\data\doc_db_aggregated.csv")
    # Example query
    query = "Căn cứ theo khoản 3 Điều 56 luật về hôn nhân quy định về công chứng di chúc như sau: Điều 56. Công chứng di chúc...."
    results = searcher.search(query, fuzzy=False)
    print(results)
    # searcher.analyze_token_database()
