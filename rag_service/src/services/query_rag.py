from dataclasses import dataclass
from typing import List, Optional, Dict
import time
import asyncio
from pydantic import BaseModel

# Imports from shared_libs
from shared_libs.llm_providers import ProviderFactory  # Use the provider factory to dynamically get providers
from shared_libs.utils.logger import Logger
from shared_libs.config.config_loader import ConfigLoader

try:
    from services.search_qdrant import search_qdrant    # Absolute import for use in production
except ImportError:
    from search_qdrant import search_qdrant    # Relative import for direct script testing

try:
    from services.get_embedding_function import get_embedding_function    # Absolute import for use in production
except ImportError:
    from get_embedding_function import get_embedding_function    # Relative import for direct script testing

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

# Load the default LLM provider using ProviderFactory, including fallback logic
provider_name = config_loader.get_config_value("llm.provider", "groq")
llm_settings = config_loader.get_config_value(f"llm.{provider_name}", {})
requirements = config_loader.get_config_value("requirements", "")
llm_provider = ProviderFactory.get_provider(name=provider_name, config=llm_settings, requirements=requirements)


class QueryResponse(BaseModel):
    query_text: str
    response_text: str
    sources: List[str]
    timestamp: int

async def local_embed(query: str) -> Optional[List[float]]:
    """
    Temporary local embedding function for development purposes.
    Replace this with a proper embedding model as needed.
    
    :param query: The input text to embed.
    :return: The embedding vector as a list of floats.
    """
    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    CACHE_DIR = "/app/models"
    try:
        import fastembed
        import numpy as np
        embedding_provider = fastembed.TextEmbedding(
            model_name=MODEL_NAME,
            cache_dir=CACHE_DIR,
            local_files_only=True  # Ensure only local models are used
        )
        embedding_generator = embedding_provider.embed(query)
        # Convert the generator to a list and then to a numpy array
        embeddings = list(embedding_generator)
        if not embeddings:
            logger.error(f"No embeddings returned for text '{query}'.")
            return []

        embedding = np.array(embeddings)

        # Handle 2D arrays with a single embedding vector
        if embedding.ndim == 2 and embedding.shape[0] == 1:
            embedding = embedding[0]

        # Ensure that the embedding is a flat array
        if embedding.ndim != 1:
            logger.error(f"Embedding for text '{query}' is not a flat array. Got shape: {embedding.shape}")
            return []

        # Log embedding norm for debugging
        embedding_norm = np.linalg.norm(embedding)
        logger.debug(f"Embedding norm for text '{query}': {embedding_norm}")

        return embedding.tolist()
    except Exception as e:
        logger.error(f"Failed to create embedding for the input: '{query}', error: {e}")
        return []
    except Exception as e:
        logger.error(f"Local embedding failed for query '{query}': {e}")
        return None
    
async def query_rag(
    query_item,
    provider: Optional[ProviderFactory] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    embedding_mode: Optional[str] = None  # Optional parameter to override default embedding mode
) -> QueryResponse:
    """
    Perform Retrieval-Augmented Generation (RAG) to answer the user's query.

    :param query_item: An object containing the query text.
    :param provider: (Optional) Override the default LLM provider.
    :param conversation_history: (Optional) List of previous conversation messages.
    :param embedding_mode: (Optional) 'local' or 'api' to override the default embedding mode.
    :return: QueryResponse containing the answer and sources.

    :param query_item: An object containing the query text.
    :param provider: (Optional) Override the default LLM provider.
    :param conversation_history: (Optional) List of previous conversation messages.
    :param embedding_mode: (Optional) 'local' or 'api' to override the default embedding mode.
    :return: QueryResponse containing the answer and sources.
    """
    query_text = query_item.query_text

    if provider is None:
        provider = llm_provider

    # Determine the embedding mode
    if embedding_mode:
        current_embedding_mode = embedding_mode.lower()
        logger.debug(f"Overriding embedding mode to: {current_embedding_mode}")
    else:
        current_embedding_mode = config_loader.get_config_value("embedding.mode", "local").lower()
        logger.debug(f"Using embedding mode from config: {current_embedding_mode}")

    # Initialize the embedding vector
    embedding_vector = None

    if current_embedding_mode == "local":
        # Use local embedding function
        embedding_vector = await local_embed(query_text)
        if embedding_vector is None:
            return QueryResponse(
                query_text=query_text,
                response_text="Đã xảy ra lỗi khi tạo embedding.",
                sources=[],
                timestamp=int(time.time())
            )
    elif current_embedding_mode == "api":
        # Use embedding microservice API
        try:
            # Retrieve the embedding service URL from the configuration
            embedding_service_url = config_loader.get_config_value("embedding.api_service_url")
            if not embedding_service_url:
                logger.error("Embedding service URL is not configured.")
                return QueryResponse(
                    query_text=query_text,
                    response_text="Đã xảy ra lỗi khi xác định URL dịch vụ embedding.",
                    sources=[],
                    timestamp=int(time.time())
                )
            
            logger.debug(f"Requesting embedding from microservice at: {embedding_service_url} for query: '{query_text}'")
            
            # Prepare the payload according to the microservice's expected schema
            payload = {
                "texts": [query_text],        # Ensure texts are in a list
                "provider": "local",          # Specify the provider; adjust if needed
                "is_batch": False             # Set to False for single query
            }
            
            # Send the POST request to the embedding microservice
            async with httpx.AsyncClient() as client:
                response = await client.post(embedding_service_url, json=payload, timeout=30.0)
                response.raise_for_status()  # Raise an exception for HTTP error responses
            
            # Parse the JSON response
            data = response.json()
            
            # Extract the embeddings from the response
            embeddings = data.get("embeddings")  # Assuming the microservice returns "embeddings"
            
            # Validate the embeddings in the response
            if not embeddings or not isinstance(embeddings, list):
                logger.error(f"No embeddings returned from microservice for query: '{query_text}'")
                return QueryResponse(
                    query_text=query_text,
                    response_text="Đã xảy ra lỗi khi nhận embedding từ dịch vụ.",
                    sources=[],
                    timestamp=int(time.time())
                )
            
            # Since we're sending a single text, extract the first embedding
            embedding_vector = embeddings[0]
            logger.debug(f"Embedding received from microservice for query: '{query_text}'")
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error when contacting embedding microservice: {str(e)}")
            return QueryResponse(
                query_text=query_text,
                response_text="Đã xảy ra lỗi khi kết nối với dịch vụ embedding.",
                sources=[],
                timestamp=int(time.time())
            )
        except Exception as e:
            logger.error(f"Unexpected error when contacting embedding microservice: {str(e)}")
            return QueryResponse(
                query_text=query_text,
                response_text="Đã xảy ra lỗi khi tạo embedding.",
                sources=[],
                timestamp=int(time.time())
            )

    else:
        logger.error(f"Unsupported embedding mode '{current_embedding_mode}'.")
        return QueryResponse(
            query_text=query_text,
            response_text="Đã xảy ra lỗi khi xác định chế độ embedding.",
            sources=[],
            timestamp=int(time.time())
        )

    # Proceed to retrieve similar documents using Qdrant
    logger.debug(f"Retrieving documents related to query: '{query_text}'")
    retrieved_docs = await search_qdrant(embedding_vector, top_k=3)
    if not retrieved_docs:
        logger.warning(f"No relevant documents found for query: '{query_text}'")
        response_text = "Không tìm thấy thông tin liên quan."
        sources = []
    else:
        # Combine retrieved documents to form context for LLM
        context = "\n\n---------------------------\n\n".join([
            f"Mã tài liệu: {doc['record_id']}\nNguồn: {doc['source']}\nNội dung: {doc['content']}"
            for doc in retrieved_docs if doc.get('content')
        ])
        logger.debug(f"Retrieved documents combined to form context for query: '{query_text}'")

        # Define the system prompt with clear citation instructions using the loaded prompt
        system_prompt = rag_prompt
        logger.debug(f"System prompt loaded for query: '{query_text}'")

        # Combine system prompt and user message to form the full prompt
        full_prompt = f"{system_prompt}\n\nCâu hỏi của người dùng: {query_text}\n\nCác câu trả lời liên quan:\n\n{context}"
        logger.debug(f"Full prompt created for query: '{query_text}'")

        # Generate response using the LLM provider
        try:
            logger.debug(f"Generating response using LLM provider")
            response_text = await provider.send_single_message(prompt=full_prompt)
        except Exception as e:
            logger.error(f"Failed to generate a response using the provider for query: '{query_text}'. Error: {str(e)}")
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
    query_text = "Tôi có thể thành lập công ty cổ phần có vốn điều lệ dưới 1 tỷ đồng không?"   
    query_item = QueryModel(query_text=query_text)
    
    # Since query_rag is an async function, we need to await its result.
    response = await query_rag(query_item=query_item,embedding_mode="api")
    print(f"Received: {response}")

if __name__ == "__main__":
    # For local testing: use asyncio.run to execute the async main function.
    asyncio.run(main())