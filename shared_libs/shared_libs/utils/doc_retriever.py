import os
import logging
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from underthesea import word_tokenize
import pickle
from typing import List, Tuple, Dict


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def compute_tfidf_similarity(query, documents):
    vectorizer = TfidfVectorizer().fit(documents)
    query_vec = vectorizer.transform([query])
    doc_vecs = vectorizer.transform(documents)
    sims = cosine_similarity(query_vec, doc_vecs).flatten()
    return sims

class DocRetriever:
    def __init__(self, csv_path: str, token_db_path: str = 'src/data/token_db.pkl'):
        """
        Initialize the DocRetriever with paths to the CSV and token database.

        :param csv_path: Path to the CSV file containing documents.
        :param token_db_path: Path to the token database pickle file.
        """
        self.csv_path = csv_path
        self.token_db_path = token_db_path
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

    @staticmethod
    def create_token_database(documents, apply_tfidf=False):
        """
        Create a token frequency database from documents with optional TF-IDF weighting.
        
        :param documents: List of document titles.
        :param apply_tfidf: Whether to apply TF-IDF weighting.
        :return: Token frequency or TF-IDF scores dictionary.
        """
        tokenized_docs = [' '.join(word_tokenize(doc.lower())) for doc in documents]
        
        if apply_tfidf:
            vectorizer = TfidfVectorizer()
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
            document_number = mention_dict['document_number']  # Add this line
            issue_year = mention_dict['issue_year']
            issuer_body = mention_dict['issuer_body']
            extra_info = mention_dict['extra_info']

            mention_matches = self.match_documents(
                mention, 
                document_type,
                document_number,     # Add this argument
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
        split_pattern = re.compile(r'\s+và\s+', re.IGNORECASE)
        segments = split_pattern.split(text)
        logger.debug(f"Segments after splitting on 'và': {segments}")

        pattern = re.compile(
            r"(?P<document_type>Luật|Bộ luật|Pháp lệnh|Nghị định|Thông tư(?: liên tịch)?|Nghị quyết|Quyết định)"
            r"(?:\s+(?P<document_number>\d{1,3}))?"
            r"(?:/(?P<issue_year>\d{4}))?"
            r"(?:/(?P<suffix>[\w\-]+))?"
            r"(?:\s+(?P<extra_info>.+))?",
            re.UNICODE | re.IGNORECASE
        )

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            match = pattern.match(segment)
            if match:
                document_type = match.group("document_type").strip().lower() if match.group("document_type") else ""
                document_number = match.group("document_number").strip() if match.group("document_number") else ""
                issue_year = match.group("issue_year").strip() if match.group("issue_year") else ""
                suffix = match.group("suffix").strip() if match.group("suffix") else ""
                extra_info = match.group("extra_info").strip() if match.group("extra_info") else ""

                # Determine the issuer body if present in extra info
                issuer_body = ""
                for body, abbrev in self.issuer_mapping.items():
                    if body in extra_info.lower():
                        issuer_body = abbrev
                        # Remove the identified issuer body from extra_info
                        extra_info = extra_info.replace(body, "").strip()

                mention_text = document_type.capitalize()
                if document_number:
                    mention_text += f" {document_number}"
                if issue_year:
                    mention_text += f"/{issue_year}"
                if suffix:
                    mention_text += f"/{suffix}"
                if extra_info:
                    mention_text += f" {extra_info}"

                mentions.append({
                    'mention': mention_text,
                    'document_type': document_type,
                    'document_number': document_number,
                    'issue_year': issue_year,
                    'issuer_body': issuer_body,
                    'extra_info': extra_info
                })
                logger.debug(f"Extracted mention: {mentions[-1]}")
            else:
                logger.debug(f"No match found for segment: '{segment}'")

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
        cutoff: float = 0.75  # Adjust as needed
    ) -> Dict[str, List[Tuple[str, str, float]]]:
        matches = defaultdict(list)

        # Adjusted weights
        weights = {
            'document_type': 0.2,
            'document_number': 0.3,  # Increased weight
            'issue_year': 0.3,
            'issuer_body': 0.2
        }
        total_weight = 0
        combined_condition = pd.Series(True, index=self.documents.index)

        # Handle equivalent document types
        if document_type:
            equivalent_types = self.equivalent_document_types.get(document_type.lower(), [document_type.lower()])
            condition = self.documents['document_type'].str.lower().isin(equivalent_types)
            combined_condition &= condition
            total_weight += weights['document_type']
        if document_number:
            condition = self.documents['document_number'].str.lower() == document_number.lower()
            combined_condition &= condition
            total_weight += weights['document_number']
        if issue_year:
            condition = self.documents['issue_year'] == issue_year
            combined_condition &= condition
            total_weight += weights['issue_year']
        if issuer_body:
            condition = self.documents['issuer_body'].str.lower() == issuer_body.lower()
            combined_condition &= condition
            total_weight += weights['issuer_body']

        # Apply conditions
        potential_matches = self.documents[combined_condition]
        logger.debug(f"Potential matches based on provided information: {len(potential_matches)}")

        # Compute confidence score based on matched properties
        confidence_score = total_weight  # Since we only included properties that matched

        # Confidence threshold (e.g., 0.7)
        confidence_threshold = 0.7
        if not potential_matches.empty and confidence_score >= confidence_threshold:
            # Collect matches with confidence score
            for _, row in potential_matches.iterrows():
                matches[mention].append((row['Full Name'], row['Document_ID'], confidence_score))
            # Sort matches by issue year in descending order
            matches[mention] = sorted(matches[mention], key=lambda x: int(self.documents.loc[self.documents['Document_ID'] == x[1], 'issue_year'].values[0]), reverse=True)
            matches[mention] = matches[mention][:top_n]
            logger.info(f"Found matches for mention '{mention}' with high confidence.")
        else:
            # Proceed to similarity search
            # Narrow down potential matches based on available properties
            potential_matches = self.documents
            equivalent_types = self.equivalent_document_types.get(document_type.lower(), [document_type.lower()])
            potential_matches = potential_matches[potential_matches['document_type'].str.lower().isin(equivalent_types)]
            if document_number:
                potential_matches = potential_matches[potential_matches['document_number'].str.lower() == document_number.lower()]
            if issuer_body:
                potential_matches = potential_matches[potential_matches['issuer_body'].str.lower() == issuer_body.lower()]
            potential_matches = potential_matches.copy()
            documents = potential_matches['Full Name'].tolist()

            # Prepare query text for similarity computation
            if extra_info:
                query_text = f"{document_type} {document_number} {extra_info}".strip().lower()
            else:
                query_text = mention.lower()

            # Compute similarity scores using TF-IDF
            similarities = compute_tfidf_similarity(query_text, documents)
            potential_matches['similarity'] = similarities

            # Filter matches based on similarity cutoff
            potential_matches = potential_matches[potential_matches['similarity'] >= cutoff]

            if not potential_matches.empty:
                # Sort matches by similarity score and issue year
                potential_matches = potential_matches.sort_values(by=['similarity', 'issue_year'], ascending=[False, False])
                # Collect matches
                for _, row in potential_matches.iterrows():
                    matches[mention].append((row['Full Name'], row['Document_ID'], row['similarity']))
                matches[mention] = matches[mention][:top_n]
                logger.info(f"Found matches for mention '{mention}' using similarity search.")
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

# Example usage
if __name__ == "__main__":
    searcher = DocRetriever("src\data\doc_db_aggregated.csv")
    query = "bộ luật dân sự."
    
    results = searcher.search(query, fuzzy=False)
    print(results)