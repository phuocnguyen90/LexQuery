# rag_service/src/services/llama_index_data_handler.py

import os
import asyncio
from typing import Callable, List, Optional, Awaitable
from dotenv import load_dotenv, find_dotenv

from llama_index import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    StorageContext,
    Settings,
    ServiceContext,
)
from llama_index.node_parser import (
    SentenceSplitter,
    SemanticSplitterNodeParser,
    SemanticDoubleMergingSplitterNodeParser,
    TopicNodeParser,
    LanguageConfig,
)
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms import LLM  # Adjust import based on your LLM integration

from shared_libs.config.app_config import AppConfigLoader
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.embeddings.embedder_factory import EmbedderFactory
from shared_libs.utils.logger import Logger

from qdrant_client import QdrantClient  # Ensure qdrant-client is installed

# Load environment variables from .env file if present
load_dotenv(find_dotenv())

logger = Logger.get_logger(module_name=__name__)


class LlamaIndexDataHandler:
    def __init__(self, chunk_size: int, chunk_overlap: int, top_k: int):
        """
        Initialize the LlamaIndexDataHandler with specified chunking parameters and top_k for querying.

        :param chunk_size: The size of each document chunk.
        :param chunk_overlap: The overlap between consecutive chunks.
        :param top_k: The number of top results to return during querying.
        """
        # Load configuration
        config_loader = AppConfigLoader()
        embedding_config = EmbeddingConfig.from_config_loader()

        # Retrieve necessary environment variables
        input_dir = os.getenv('INPUT_DIR')
        collection_name = os.getenv('QA_COLLECTION_NAME')
        qdrant_url = os.getenv('QDRANT_URL')
        qdrant_api_key = os.getenv('QDRANT_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'groq')  # e.g., 'groq', 'openai', etc.

        # Initialize Settings
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

        self.top_k = top_k
        self.collection_name = collection_name

        # Initialize Embedder using EmbedderFactory
        try:
            self.embedder = EmbedderFactory.create_embedder(embedding_config.default_provider)
            logger.info(f"Initialized embedder for provider '{embedding_config.default_provider}'.")
        except Exception as e:
            logger.error(f"Failed to initialize embedder: {e}")
            raise e

        # Initialize Qdrant client
        try:
            self.qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            logger.info("Initialized Qdrant client successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise e

        # Set up Qdrant vector store
        self.qdrant_vector_store = QdrantVectorStore(
            collection_name=self.collection_name,
            client=self.qdrant_client,
        )

        # Set up StorageContext with Qdrant vector store
        self.storage_ctx = StorageContext.from_defaults(vector_store=self.qdrant_vector_store)

        # Initialize Sentence Splitter
        self.sentence_splitter = SentenceSplitter.from_defaults(
            chunk_size=Settings.chunk_size,
            chunk_overlap=Settings.chunk_overlap
        )

        # Load documents from the specified directory
        self.documents = self.load_documents(input_dir)

        # Initialize VectorStoreIndex (to be created based on method)
        self.vector_store_index: Optional[VectorStoreIndex] = None

    def load_documents(self, input_dir: str) -> List:
        """
        Load documents from the specified directory.

        :param input_dir: Directory containing the documents.
        :return: List of loaded documents.
        """
        if not input_dir:
            logger.error("Input directory not specified.")
            raise ValueError("Input directory must be specified via 'INPUT_DIR' environment variable.")

        logger.info(f"Loading documents from directory: {input_dir}")
        return SimpleDirectoryReader(input_dir=input_dir, required_exts=['.pdf']).load_data(show_progress=True)

    def index_data_based_on_method(self, method: str):
        """
        Index documents based on the specified chunking method.

        :param method: Chunking method to use ('semantic_chunking', 'semantic_double_merge_chunking', 'topic_node_parser').
        """
        logger.info(f"Indexing data using method: '{method}'")
        if method == 'semantic_chunking':
            splitter = SemanticSplitterNodeParser(
                buffer_size=1,
                breakpoint_percentile_threshold=95,
                embed_model=self.embedder
            )
            nodes = splitter.get_nodes_from_documents(documents=self.documents)

        elif method == 'semantic_double_merge_chunking':
            config = LanguageConfig(language="english", spacy_model="en_core_web_md")
            splitter = SemanticDoubleMergingSplitterNodeParser(
                language_config=config,
                initial_threshold=0.4,
                appending_threshold=0.5,
                merging_threshold=0.5,
                max_chunk_size=5000,
                embed_model=self.embedder
            )
            nodes = splitter.get_nodes_from_documents(documents=self.documents)

        elif method == 'topic_node_parser':
            llm = self.initialize_llm(provider=os.getenv('LLM_PROVIDER', 'groq'))
            node_parser = TopicNodeParser.from_defaults(
                llm=llm,
                max_chunk_size=Settings.chunk_size,
                similarity_method="llm",
                similarity_threshold=0.8,
                window_size=3
            )
            nodes = node_parser.get_nodes_from_documents(documents=self.documents)

        else:
            logger.error(f"Unsupported indexing method: '{method}'")
            raise ValueError(f"Unsupported indexing method: '{method}'")

        # Check if the Qdrant collection exists
        if not self.qdrant_client.collection_exists(collection_name=self.collection_name):
            logger.info(f"Collection '{self.collection_name}' does not exist. Creating new collection.")
            # Here, you might want to define your collection parameters based on your use case
            self.qdrant_client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_client.models.VectorParams(
                    size=self.embedder.vector_dimension,
                    distance=qdrant_client.models.Distance.COSINE
                )
            )
            logger.info(f"Collection '{self.collection_name}' created successfully.")

        # Create or load VectorStoreIndex
        if not self.vector_store_index:
            self.vector_store_index = VectorStoreIndex(
                nodes=nodes,
                storage_context=self.storage_ctx,
                show_progress=True,
                transformations=[self.sentence_splitter]
            )
            logger.info("VectorStoreIndex created successfully.")
        else:
            logger.info("VectorStoreIndex already exists. Loading from vector store.")
            self.vector_store_index = VectorStoreIndex.from_vector_store(
                vector_store=self.qdrant_vector_store
            )

    def initialize_llm(self, provider: str) -> LLM:
        """
        Initialize the LLM based on the provider specified.

        :param provider: The LLM provider to use (e.g., 'groq', 'openai').
        :return: Initialized LLM instance.
        """
        logger.info(f"Initializing LLM provider: '{provider}'")
        if provider.lower() == 'groq':
            llm_url = os.getenv('LLM_URL')
            llm_model = os.getenv('LLM_MODEL')
            llm = LLM(
                provider='groq',
                base_url=llm_url,
                model=llm_model,
                request_timeout=300
            )
            logger.info("Groq LLM initialized successfully.")
            return llm

        elif provider.lower() == 'openai':
            # Initialize OpenAI LLM (assuming you have a corresponding class or setup)
            from llama_index.llms.openai import OpenAI  # Adjust import based on actual implementation
            openai_api_key = os.getenv('OPENAI_API_KEY')
            llm = OpenAI(api_key=openai_api_key, model=os.getenv('OPENAI_MODEL', 'text-davinci-003'))
            logger.info("OpenAI LLM initialized successfully.")
            return llm

        else:
            logger.error(f"Unsupported LLM provider: '{provider}'")
            raise ValueError(f"Unsupported LLM provider: '{provider}'")

    def create_query_engine(self) -> Callable[[str], Awaitable[str]]:
        """
        Create a query engine from the VectorStoreIndex.

        :return: A callable query engine function.
        """
        if not self.vector_store_index:
            logger.error("VectorStoreIndex is not initialized. Please index data first.")
            raise ValueError("VectorStoreIndex is not initialized. Please index data first.")

        logger.info("Creating query engine from VectorStoreIndex.")
        return self.vector_store_index.as_query_engine(top_k=self.top_k)

    async def query(self, query_text: str) -> Optional[str]:
        """
        Execute a query against the indexed data.

        :param query_text: The query string.
        :return: The query result as a string, or None if failed.
        """
        try:
            query_engine = self.create_query_engine()
            response = await asyncio.to_thread(query_engine.query, query_text)
            logger.debug(f"Query response: {response}")
            return str(response)
        except Exception as e:
            logger.error(f"Query failed for text '{query_text}': {e}")
            return None


# Usage example
def main():
    # Define chunking parameters and top_k
    chunk_size = 128
    chunk_overlap = 20
    top_k = 3

    # Initialize the data handler
    llama_index_handler = LlamaIndexDataHandler(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k
    )

    # Index data using a specific chunking method
    llama_index_handler.index_data_based_on_method(method='semantic_double_merge_chunking')

    # Example query
    query_text = "Operational challenges of MLOps"
    response = asyncio.run(llama_index_handler.query(query_text))
    print(response)


if __name__ == "__main__":
    main()
