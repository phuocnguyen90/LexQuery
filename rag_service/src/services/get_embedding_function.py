# rag_service/src/services/get_embedding_function.py

from typing import Callable, List, Optional
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

async def local_embed(query: str) -> Optional[List[float]]:
    """
    Temporary local embedding function for development purposes.
    Replace this with a proper embedding model as needed.
    
    :param query: The input text to embed.
    :return: The embedding vector as a list of floats.
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        embedding = model.encode(query).tolist()
        logger.debug(f"Local embedding generated for query: '{query}'")
        return embedding
    except Exception as e:
        logger.error(f"Local embedding failed for query '{query}': {e}")
        return None

def get_embedding_function() -> Callable[[str], List[float]]:
    """
    Returns the local embedding function for development purposes.
    
    :return: A function that takes a string and returns its embedding vector.
    """
    return local_embed
