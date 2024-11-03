# embedding_service\src\main.py

from fastapi import FastAPI, HTTPException
from shared_libs.embeddings.embedder_factory import EmbedderFactory
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.utils.logger import Logger
from shared_libs.models.embed_models import EmbeddingRequest, EmbeddingResponse

from shared_libs.config import AppConfigLoader
import uvicorn
import os

app_config=AppConfigLoader()


logger = Logger.get_logger(module_name=__name__)

app = FastAPI(
    title="Embedding Service",
    description="Provides text embeddings using various pre-trained models.",
    version="1.0.0",
)


def startup_event():
    """
    Initialize all embedders at startup to ensure they're ready to handle requests.
    """
    try:
        # Load configuration
        embedding_config = EmbeddingConfig.from_config_loader()

        # Initialize API-based providers
        for provider_key, config in embedding_config.api_providers.items():
            EmbedderFactory.create_embedder(config)

        # Initialize library-based providers
        for provider_key, config in embedding_config.library_providers.items():
            EmbedderFactory.create_embedder(config)

        logger.info("All embedders initialized and cached successfully.")

    except Exception as e:
        logger.error(f"Failed to initialize embedders: {e}")
        raise e  # Optionally, stop the server if embedders fail to initialize

startup_event()

@app.post("/embed", response_model=EmbeddingResponse)
async def get_embeddings(request: EmbeddingRequest):
    """
    Generate embeddings for a list of input texts using the specified provider.
    """
    provider = request.provider.lower() if request.provider else "local"  # Default to 'local'
    is_batch = request.is_batch  # Whether to use batch embedding or not

    try:

        # Attempt to decode the JSON

        if isinstance(request.texts, str):
            # Split the multi-line string into separate lines
            texts = [line.strip() for line in request.texts.splitlines() if line.strip()]
        else:
            texts = request.texts

        if not texts:
            raise ValueError("No texts provided for embedding.")

        # Load configuration
        embedding_config = EmbeddingConfig.from_config_loader()

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
        if is_batch:
            embeddings = embedder.batch_embed(texts)  # Should return List[List[float]]
        else:
            if len(request.texts) != 1:
                raise HTTPException(status_code=400, detail="Single embedding request should contain exactly one text.")
            embedding = embedder.embed(texts[0])  # Should return List[float]
            embeddings = [embedding]
        # Validate embeddings
        if not all(embeddings):
            logger.error("One or more embeddings could not be generated.")
            raise HTTPException(status_code=500, detail="Embedding generation failed for some texts.")

        logger.info(f"Successfully generated embeddings for provider '{provider}' with {len(request.texts)} texts.")
        return EmbeddingResponse(embeddings=embeddings)

    except ValueError as ve:
        logger.error(str(ve))
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify that the server is running.
    """
    return {"status": "ok"}

# Local Development Function to Test API Endpoints
if __name__ == "__main__":
    # Retrieve port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Running the FastAPI server on {host}:{port} for local testing.")
    uvicorn.run("main:app", host=host, port=port)
