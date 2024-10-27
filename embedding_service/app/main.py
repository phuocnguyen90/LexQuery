# app/main.py

from fastapi import FastAPI, HTTPException
from app.models import EmbeddingRequest, EmbeddingResponse
from embeddings.embedder_factory import EmbedderFactory
from config.embedding_config import EmbeddingConfig
from shared_libs.utils.logger import Logger

logger = Logger.get_logger(module_name=__name__)

app = FastAPI(
    title="Embedding Service",
    description="Provides text embeddings using various pre-trained models.",
    version="1.0.0"
)

# Load configuration
embedding_config = EmbeddingConfig()  # Ensure this loads your configuration appropriately

@app.on_event("startup")
def startup_event():
    """
    Initialize all embedders at startup to ensure they're ready to handle requests.
    """
    try:
        for provider, config in embedding_config.api_providers.items():
            EmbedderFactory.create_embedder(config)
        for provider, config in embedding_config.library_providers.items():
            EmbedderFactory.create_embedder(config)
        logger.info("All embedders initialized and cached successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize embedders: {e}")
        raise e  # Optionally, stop the server if embedders fail to initialize

@app.post("/embed", response_model=EmbeddingResponse)
def get_embeddings(request: EmbeddingRequest):
    """
    Generate embeddings for a list of input texts using the specified provider.
    """
    provider = request.provider.lower() if request.provider else "local"  # Default to 'local'

    try:
        # Retrieve the specific configuration for the provider
        if provider in embedding_config.api_providers:
            config = embedding_config.api_providers[provider]
        elif provider in embedding_config.library_providers:
            config = embedding_config.library_providers[provider]
        else:
            raise ValueError(f"Provider '{provider}' is not configured.")

        # Get the embedder instance
        embedder = EmbedderFactory.create_embedder(config)

        # Generate embeddings
        embeddings = embedder.embed(request.texts)

        # Validate embeddings
        if not all(embeddings):
            logger.error("One or more embeddings could not be generated.")
            raise HTTPException(status_code=500, detail="Embedding generation failed for some texts.")

        return EmbeddingResponse(embeddings=embeddings)

    except ValueError as ve:
        logger.error(str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")
