from dataclasses import dataclass
from typing import List, Optional, Dict
import re
import time
import asyncio
import httpx
import os

# Imports from shared_libs
from shared_libs.llm_providers import ProviderFactory  # Use the provider factory to dynamically get providers
from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import ConfigLoader

try:
    from services.search_qdrant import search_qdrant    # Absolute import for use in production
except ImportError:
    from search_qdrant import search_qdrant    # Relative import for direct script testing


# Load configuration
config_loader = ConfigLoader()  

# Configure logging
logger = Logger.get_logger(module_name=__name__)

# Load the RAG prompt from config
rag_prompt = config_loader.get_prompt("prompts.rag_prompt.system_prompt")

# Log an appropriate warning if the prompt is empty
if not rag_prompt:
    logger.warning("RAG system prompt is empty or not found in prompts configuration.")
else:
    logger.info("RAG system prompt loaded successfully.")

# Load the default provider using ProviderFactory, including fallback logic
provider_name = config_loader.get_config_value("provider", "groq")
llm_settings = config_loader.get_config_value(provider_name, {})
requirements = config_loader.get_config_value("requirements", "")
llm_provider = ProviderFactory.get_provider(name=provider_name, config=llm_settings, requirements=requirements)

# Load EMBEDDING_MODE
EMBEDDING_MODE = config_loader.get_config_value("embedding.mode", "ec2").lower()

# Embedding Service URL based on EMBEDDING_MODE
if EMBEDDING_MODE == "local":
    EMBEDDING_SERVICE_URL = None  # Not needed for local mode
elif EMBEDDING_MODE == "docker":
    EMBEDDING_SERVICE_URL = "http://localhost:8000/embed"
elif EMBEDDING_MODE == "ec2":
    EMBEDDING_SERVICE_URL = config_loader.get_config_value("EMBEDDING_SERVICE_URL", "http://embedding-service-public-dns:8000/embed")
else:
    logger.warning(f"Unknown EMBEDDING_MODE '{EMBEDDING_MODE}'. Defaulting to 'ec2'.")
    EMBEDDING_MODE = "ec2"
    EMBEDDING_SERVICE_URL = config_loader.get_config_value("EMBEDDING_SERVICE_URL", "http://embedding-service-public-dns:8000/embed")

@dataclass
class QueryResponse:
    query_text: str
    response_text: str
    sources: List[str]
    timestamp: int

async def query_rag(query_item, provider=None, conversation_history: Optional[List[Dict[str, str]]] = None) -> QueryResponse:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query.
    """
    query_text = query_item.query_text

    if provider is None:
        provider = llm_provider

    # Proceed to retrieve similar documents using Qdrant
    logger.debug(f"Retrieving documents related to query: {query_text}")
    retrieved_docs = await search_qdrant(query_text, top_k=3)
    if not retrieved_docs:
        logger.warning(f"No relevant documents found for query: {query_text}")
        response_text = "Không tìm thấy thông tin liên quan."
        sources = []
    else:
        # Combine retrieved documents to form context for LLM
        context = "\n\n---------------------------\n\n".join([
            f"Mã tài liệu: {doc['record_id']}\nNguồn: {doc['source']}\nNội dung: {doc['content']}"
            for doc in retrieved_docs if doc.get('content')
        ])
        logger.debug(f"Retrieved documents combined to form context for query: {query_text}")

        # Define the system prompt with clear citation instructions using the loaded prompt
        system_prompt = rag_prompt
        logger.debug(f"System prompt loaded for query: {query_text}")

        # Combine system prompt and user message to form the full prompt
        full_prompt = f"{system_prompt}\n\nCâu hỏi của người dùng: {query_text}\n\nCác câu trả lời liên quan:\n\n{context}"
        logger.debug(f"Full prompt created for query: {query_text}")

        # Route based on EMBEDDING_MODE
        if EMBEDDING_MODE == "local":
            # Use local fastembed library
            try:
                logger.debug(f"Using local fastembed for query: {query_text}")
                response_text = await provider.send_single_message(prompt=full_prompt)
            except Exception as e:
                logger.error(f"Failed to generate a response using the local provider for query: {query_text}. Error: {str(e)}")
                response_text = "Đã xảy ra lỗi khi tạo câu trả lời."
        elif EMBEDDING_MODE in ["docker", "ec2"]:
            # Use embedding service via HTTP
            try:
                logger.debug(f"Sending request to embedding service ({EMBEDDING_MODE}) for query: {query_text}")
                async with httpx.AsyncClient() as client:
                    payload = {"prompt": full_prompt, "conversation_history": conversation_history or []}
                    response = await client.post(EMBEDDING_SERVICE_URL, json=payload, timeout=30.0)
                    response.raise_for_status()
                    data = response.json()
                    response_text = data.get("response_text", "Đã xảy ra lỗi khi tạo câu trả lời.")
            except httpx.HTTPError as e:
                logger.error(f"HTTP error when contacting embedding service: {str(e)}")
                response_text = "Đã xảy ra lỗi khi tạo câu trả lời."
            except Exception as e:
                logger.error(f"Unexpected error when contacting embedding service: {str(e)}")
                response_text = "Đã xảy ra lỗi khi tạo câu trả lời."
        else:
            logger.error(f"Unsupported EMBEDDING_MODE '{EMBEDDING_MODE}'.")
            response_text = "Đã xảy ra lỗi khi tạo câu trả lời."

        # Add citations to the response based on retrieved document IDs
        if retrieved_docs:
            citation_texts = [f"[Mã tài liệu: {doc['record_id']}]" for doc in retrieved_docs if doc.get('content')]
            if citation_texts:
                response_text += "\n\nNguồn tham khảo: " + ", ".join(citation_texts)

        # Extract sources from retrieved_docs
        sources = [doc['record_id'] for doc in retrieved_docs]
    # Create and return the QueryResponse
    response = QueryResponse(
        query_text=query_text,
        response_text=response_text,
        sources=sources,
        timestamp=int(time.time())
    )
    return response

# For local testing
async def main():
    """
    For local testing.
    """
    logger.debug("Running example RAG call.")
    import os
    import sys
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    from models.query_model import QueryModel  # Import your QueryModel
    query_text = "Tôi có thể đặt tên doanh nghiệp bằng tiếng Anh được không?"   
    query_item = QueryModel(query_text=query_text)
    
    # Since query_rag is an async function, we need to await its result.
    response = await query_rag(query_item)
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing: use asyncio.run to execute the async main function.
    asyncio.run(main())