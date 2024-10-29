# shared_libs\shared_libs\models\embed_models.py

from pydantic import BaseModel, Field
from typing import List, Optional

# Define Pydantic models 
class EmbeddingRequest(BaseModel):
    texts: List[str] = Field(
        ...,
        example=["Hello world", "FastAPI is awesome!"],
        description="List of texts to generate embeddings for."
    )
    provider: Optional[str] = Field(
        None,
        description="Embedding provider to use. Options: 'local', 'bedrock', 'openai_embedding', 'google_gemini_embedding', etc.",
        example="local"
    )
    is_batch: bool = Field(
        False,
        description="Whether to use batch embedding or not."
    )

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]] = Field(
        ...,
        description="List of embedding vectors corresponding to the input texts."
    )
