import os
import time
import re
import json
import numpy as np
import asyncio
from typing import List, Optional, Dict, Any, Callable
from pydantic import BaseModel

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import shared utilities
from shared_libs.utils.logger import Logger

# Import PromptConfigLoader if needed
from shared_libs.config.prompt_config import PromptConfigLoader
from shared_libs.llm_providers.llm_provider import LLMProvider  
from models.query_model import QueryModel

logger = Logger.get_logger(module_name=__name__)

class QueryResponse(BaseModel):
    query_text: str
    response_text: str
    sources: List[str]
    timestamp: int

DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() in ["true", "1", "yes"]

async def query_rag(
    query_item:QueryModel,
    conversation_history: Optional[List] = None,
    provider: Optional[LLMProvider] = None,
    embedding_mode: Optional[str] = None,
    llm_provider_name: Optional[str] = None,
    rerank: bool = False,
    keyword_gen: bool = False,
    config: Optional[Dict[str, Any]] = None,
    embedding_config: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query.
    
    Optional parameters:
      - config: A configuration dictionary. If not provided, it will be loaded via AppConfigLoader.
      - embedding_config: Embedding-specific configuration. If not provided, it is loaded from shared_libs.
      - embedding_mode: 'local' or 'api'. If not provided, it is taken from env or the config.
      
    Returns a dictionary with a query_response and retrieved_docs.
    """
    # Load the global configuration if not provided.
    if config is None:
        from shared_libs.config import Config
        
        global_config = Config.load()
        embedding_config = global_config.embedding
        llm_config = global_config.llm
        qdrant_config = global_config.qdrant
    else:
        # Create a dummy loader if necessary
        from shared_libs.config.app_config import AppConfigLoader
        app_config = AppConfigLoader()
    
    # Load embedding configuration if not provided.
    if embedding_config is None:
        from shared_libs.config.embedding_config import EmbeddingConfig
        embedding_config = EmbeddingConfig.get_embed_config(app_config)
    
    # Determine embedding mode, using environment variable or config defaults.
    if embedding_mode is None:
        embedding_mode = os.getenv('EMBEDDING_MODE', config.get('embedding', {}).get('mode', 'local')).lower()
    
    # Initialize the embedder factory with the embedding_config.
    from shared_libs.embeddings.embedder_factory import EmbedderFactory
    factory = EmbedderFactory(embedding_config)
    
    # Determine and create the embedding function based on the mode.
    if embedding_mode == "api":
        embedding_function = factory.create_embedder('cloud')
    elif embedding_mode == "local":
        embedding_function = factory.create_embedder('local')
    else:
        raise ValueError(f"Unsupported embedding mode: {embedding_mode}")
    
    if provider is None:
        from services.query_rag import initialize_provider  # or adjust the import as needed
        provider = initialize_provider(llm_config.llm.get('provider', 'groq'))

    
    # Generate the embedding vector for the query text.
    # Note: generate_embedding is expected to be an async function.
    from services.query_rag import generate_embedding  # ensure correct import if necessary
    embedding_vector = await generate_embedding(query_item.query_text, embedding_function)
    if embedding_vector is None:
        fallback_response = QueryResponse(
            query_text=query_item.query_text,
            response_text="An error occurred while creating embedding.",
            sources=[],
            timestamp=int(time.time())
        )
        return {
            "query_response": fallback_response.model_dump(),
            "retrieved_docs": [] if DEVELOPMENT_MODE else None
        }
    
    # Set collection names from environment variables or config defaults.
    QA_COLLECTION_NAME = os.getenv("QA_COLLECTION_NAME", "legal_qa")
    DOC_COLLECTION_NAME = os.getenv("DOC_COLLECTION_NAME", "legal_doc")
    all_retrieved_docs = []
    
    # Initialize extra logging variables.
    extracted_keywords = []
    rerank_applied = False
    
    if keyword_gen:
        for attempt in range(2):
            try:
                logger.debug(f"Attempt {attempt + 1}: Extracting keywords for query: {query_item.query_text}")
                # Call the extract_keywords method from query_rag (assuming it is async)
                from services.query_rag import extract_keywords
                keywords = await extract_keywords(query_item.query_text, provider, top_k=10)
                if isinstance(keywords, list) and len(keywords) > 0:
                    logger.debug(f"Keywords extracted: {keywords}")
                    extracted_keywords = keywords
                    # Advanced search using keywords.
                    from services.search_qdrant import advanced_qdrant_search
                    qa_docs = await advanced_qdrant_search(
                        embedding_vector, keywords, collection_name=QA_COLLECTION_NAME, top_k=3
                    )
                    doc_chunks = await advanced_qdrant_search(
                        embedding_vector, keywords, collection_name=DOC_COLLECTION_NAME, top_k=6
                    )
                    all_retrieved_docs = qa_docs + doc_chunks
                    break
                else:
                    logger.warning("Keyword extraction returned an invalid or empty list.")
            except Exception as e:
                logger.error(f"Error during keyword extraction: {e}")
        
        if not all_retrieved_docs:
            logger.warning("Falling back to normal search_qdrant due to keyword generation failure.")
            from services.search_qdrant import search_qdrant
            qa_docs = await search_qdrant(embedding_vector, collection_name=QA_COLLECTION_NAME, top_k=3)
            doc_chunks = await search_qdrant(embedding_vector, collection_name=DOC_COLLECTION_NAME, top_k=6)
            all_retrieved_docs = qa_docs + doc_chunks
    else:
        from services.search_qdrant import search_qdrant
        qa_docs = await search_qdrant(embedding_vector, collection_name=QA_COLLECTION_NAME, top_k=3)
        doc_chunks = await search_qdrant(embedding_vector, collection_name=DOC_COLLECTION_NAME, top_k=6)
        all_retrieved_docs = qa_docs + doc_chunks

    if not all_retrieved_docs:
        logger.warning(f"No relevant documents found for query: '{query_item.query_text}'")
        response_text = "No relevant data found."
        fallback_response = QueryResponse(
            query_text=query_item.query_text,
            response_text=response_text,
            sources=[],
            timestamp=int(time.time())
        )
        return {
            "query_response": fallback_response.model_dump(),
            "retrieved_docs": [] if DEVELOPMENT_MODE else None,
            "keywords": extracted_keywords,
            "rerank_applied": False,
        }
    
    if rerank:
        try:
            from services.reranker import Reranker, map_qdrant_rerank, map_rerank_qdrant
            mapped_results = map_qdrant_rerank(all_retrieved_docs)
            # Example: using crossencoder for reranking
            # reranker = Reranker(method="crossencoder", model="bkai-foundation-models/vietnamese-bi-encoder")
            reranker = Reranker(method="phoranker")
            reranked_docs = reranker.rerank(query_item.query_text, mapped_results)
            all_retrieved_docs = map_rerank_qdrant(reranked_docs, all_retrieved_docs)
            rerank_applied = True
        except Exception as e:
            logger.error(f"Reranker failed: {e}")
            fallback_response = QueryResponse(
                query_text=query_item.query_text,
                response_text="An error occurred during reranking.",
                sources=[],
                timestamp=int(time.time())
            )
            return {
                "query_response": fallback_response.model_dump(),
                "retrieved_docs": [] if DEVELOPMENT_MODE else None,
                "keywords": extracted_keywords,
                "rerank_applied": False,
            }
    
    # Ensure each document has a reconstructed source if missing.
    from services.search_qdrant import reconstruct_source
    for doc in all_retrieved_docs:
        if not doc.get("source"):
            doc["source"] = reconstruct_source(doc.get("chunk_id", "Unknown Record"))
    
    # Generate the final response using an LLM.
    from services.query_rag import generate_llm_response, create_final_response
    response_text = await generate_llm_response(query_item.query_text, all_retrieved_docs, provider)
    query_response = create_final_response(query_item.query_text, response_text, all_retrieved_docs)
    
    return {
        "query_response": query_response.model_dump(),
        "retrieved_docs": all_retrieved_docs if DEVELOPMENT_MODE else None,
        "debug_prompt": None,
        "keywords": extracted_keywords,
        "rerank_applied": rerank_applied,
    }
