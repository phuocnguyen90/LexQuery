# app/main.py

from fastapi import HTTPException


from shared_libs.embeddings.embedder_factory import EmbedderFactory
from shared_libs.config.embedding_config import EmbeddingConfig
from shared_libs.utils.logger import Logger
from shared_libs.models.embed_models import EmbeddingRequest, EmbeddingResponse

from shared_libs.config import AppConfigLoader

app_config=AppConfigLoader()


logger = Logger.get_logger(module_name=__name__)

def get_embeddings(request: EmbeddingRequest):
    """
    Generate embeddings for a list of input texts using the specified provider.
    """
    provider = request.provider.lower() if request.provider else "local"  # Default to 'local'
    is_batch = request.is_batch  # Whether to use batch embedding or not

    try:
        # Load configuration
        embedding_config = EmbeddingConfig.get_embed_config(app_config)

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
            embeddings = embedder.batch_embed(request.texts)
        else:
            if len(request.texts) != 1:
                raise HTTPException(status_code=400, detail="Single embedding request should contain exactly one text.")
            embeddings = [embedder.embed(request.texts[0])]

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
