# embedding_service\src\main.py

from fastapi import FastAPI, HTTPException, Depends
from shared_libs.embeddings.embedder_factory import EmbedderFactory
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.utils.logger import Logger
from shared_libs.models.embed_models import EmbeddingRequest, EmbeddingResponse
from shared_libs.embeddings.base_embedder import BaseEmbedder
from shared_libs.embeddings.embedder_registry import EmbedderRegistry


from shared_libs.config import AppConfigLoader
import uvicorn
import os

try:
    from shared_libs.embeddings.local_embedder import LocalEmbedder # Example
except ImportError as e:
    # Handle this gracefully, maybe log a warning or raise if essential embedders are missing
    print(f"Warning: Could not import all embedder modules: {e}")


logger = Logger.get_logger(module_name=__name__)


# --- CRITICAL: Import Embedder Modules to Register Them ---
logger.info("Importing embedder modules for registration...")
try:
    # Adjust these paths to where your actual embedder CLASS definitions are
    from shared_libs.embeddings.cloud_embedder import CloudEmbedder
    from shared_libs.embeddings.local_embedder import LocalEmbedder # If local_embedder.py is in src/embeddings
    # from shared_libs.embeddings.docker_embedder import DockerEmbedder # if you have it
    from shared_libs.embeddings.bedrock_embedder import BedrockEmbedder
    from shared_libs.embeddings.openai_embedder import OpenAIEmbedder
    # ... import ALL other embedder modules you intend to use ...
    # Example for fastembed if it's a distinct embedder class and not just used by LocalEmbedder
    # from shared_libs.embeddings.fastembed_embedder import FastEmbedEmbedder # (if it exists)
    logger.info(f"EmbedderRegistry contents after imports: {EmbedderRegistry._registry.keys()}")
except ImportError as e:
    logger.error(f"Failed to import one or more embedder modules: {e}", exc_info=True)
    # Decide if this is fatal
# --- End Embedder Module Imports ---

app_config=AppConfigLoader()


app = FastAPI(
    title="Embedding Service",
    description="Provides text embeddings using various pre-trained models.",
    version="1.0.0",
)

embedder_factory_instance: EmbedderFactory = None
initialized_embedders: dict[str, BaseEmbedder] = {}

# Wrapper for the dependency to access request provider
async def get_embedder_dependency_wrapper(request: EmbeddingRequest) -> BaseEmbedder:
    provider_name = request.provider.lower() if request.provider else "local" # Default to 'local'
    return get_embedder(provider_name)


@app.on_event("startup")
async def startup_event():
    """
    Initialize EmbedderFactory and all configured embedders at startup.
    """
    global embedder_factory_instance, initialized_embedders
    try:
        logger.info("Initializing embedding service...")
        # Load main embedding configuration
        # Assuming get_embed_config returns an EmbeddingConfig instance
        main_embedding_config = EmbeddingConfig.get_embed_config(app_config)
        if not main_embedding_config:
            raise ValueError("Failed to load main embedding configuration.")

        # Initialize the EmbedderFactory with the main configuration
        embedder_factory_instance = EmbedderFactory(config=main_embedding_config)
        logger.info(f"EmbedderFactory initialized with dimension: {embedder_factory_instance.dim}")

        # Determine all providers to initialize
        providers_to_initialize = set()
        if main_embedding_config.api_providers:
            providers_to_initialize.update(main_embedding_config.api_providers.keys())
        if main_embedding_config.library_providers:
            providers_to_initialize.update(main_embedding_config.library_providers.keys())
        
        if not providers_to_initialize:
            logger.warning("No providers found in api_providers or library_providers. No embedders will be initialized.")
            return

        logger.info(f"Found providers to initialize: {list(providers_to_initialize)}")

        for provider_name in providers_to_initialize:
            try:
                logger.info(f"Initializing embedder for provider: '{provider_name}'...")
                # The factory uses the provider_name to look up its specific config and create it
                embedder = embedder_factory_instance.create_embedder(provider_name)
                initialized_embedders[provider_name.lower()] = embedder
                logger.info(f"Successfully initialized and cached embedder for provider: '{provider_name}'")
            except Exception as e_provider:
                logger.error(f"Failed to initialize embedder for provider '{provider_name}': {e_provider}", exc_info=True)
                # Decide if failure for one provider is fatal for the app
                # For now, we'll let the app start but log the error.

        if not initialized_embedders:
            logger.error("No embedders were successfully initialized. The service might not function correctly.")
            # raise RuntimeError("Critical failure: No embedders could be initialized.") # Optional: make it fatal
        else:
            logger.info(f"Successfully initialized embedders for: {list(initialized_embedders.keys())}")
        logger.info("Embedding service startup complete.")

    except Exception as e:
        logger.error(f"Critical error during embedding service startup: {e}", exc_info=True)
        # This error is likely fatal for the service
        raise RuntimeError(f"Failed to initialize embedding service: {e}") from e


def get_embedder(provider_name: str) -> BaseEmbedder:
    """
    Dependency to get a pre-initialized embedder.
    """
    embedder = initialized_embedders.get(provider_name.lower())
    if not embedder:
        logger.error(f"Requested provider '{provider_name}' not found or not initialized.")
        raise HTTPException(
            status_code=404,
            detail=f"Provider '{provider_name}' is not available or not configured."
        )
    return embedder


@app.post("/embed", response_model=EmbeddingResponse)
async def get_embeddings(request: EmbeddingRequest, embedder: BaseEmbedder = Depends(get_embedder_dependency_wrapper)):
    """
    Generate embeddings for a list of input texts using the specified provider.
    The provider name is extracted from the request and used by the dependency.
    """
    # Provider name for the dependency to resolve
    # This slightly awkward wrapper is because Depends needs a callable,
    # and we need to pass the provider name from the request to that callable.
    # A more complex dependency class could also be used.

    # The `embedder` argument is now resolved by FastAPI using `get_embedder`
    # which uses the `request.provider` value.

    try:
        if isinstance(request.texts, str):
            texts_to_embed = [line.strip() for line in request.texts.splitlines() if line.strip()]
        else:
            texts_to_embed = request.texts

        if not texts_to_embed:
            raise ValueError("No texts provided for embedding.")

        logger.info(f"Processing {len(texts_to_embed)} texts with provider '{request.provider}'. Batch: {request.is_batch}")

        if request.is_batch:
            embeddings = embedder.batch_embed(texts_to_embed)
        else:
            if len(texts_to_embed) != 1:
                raise ValueError("Single embedding request (is_batch=False) should contain exactly one text.")
            embedding = embedder.embed(texts_to_embed[0])
            embeddings = [embedding]

        # A more robust validation might be needed depending on embedder behavior
        if not embeddings or not all(isinstance(emb, list) and emb for emb in embeddings):
            logger.error(f"Embedding generation failed for provider '{request.provider}'. Empty or invalid embeddings returned.")
            raise HTTPException(status_code=500, detail="Embedding generation failed or returned invalid results.")

        logger.info(f"Successfully generated {len(embeddings)} embeddings for provider '{request.provider}'.")
        return EmbeddingResponse(embeddings=embeddings, provider=request.provider, model_name=getattr(embedder, 'model_name', 'N/A'))

    except ValueError as ve:
        logger.warning(f"Validation error for provider '{request.provider}': {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed for provider '{request.provider}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during embedding generation: {str(e)}")




@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify that the server is running and embedders are initialized.
    """
    if not embedder_factory_instance:
        return {"status": "degraded", "reason": "EmbedderFactory not initialized."}
    if not initialized_embedders:
        return {"status": "degraded", "reason": "No embedders initialized."}
    return {
        "status": "ok",
        "initialized_providers": list(initialized_embedders.keys()),
        "default_dimension": embedder_factory_instance.dim if embedder_factory_instance else "N/A"
    }

# Removed the direct call to startup_event() here.
# FastAPI handles this with @app.on_event("startup")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting FastAPI server on {host}:{port} for local development.")
    # uvicorn.run("main:app", host=host, port=port, reload=True) # reload=True is useful for dev
    uvicorn.run(app, host=host, port=port) # More direct way to run if app object is in scope