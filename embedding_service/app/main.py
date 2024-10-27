# app/main.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from models import EmbeddingModel

app = FastAPI(
    title="Embedding Service",
    description="Provides text embeddings using a pre-trained Sentence Transformer model.",
    version="1.0.0"
)

class EmbeddingRequest(BaseModel):
    texts: list[str]

class EmbeddingResponse(BaseModel):
    embeddings: list[list[float]]

# Initialize the embedding model when the server starts
model = EmbeddingModel("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

@app.post("/embed", response_model=EmbeddingResponse)
def get_embeddings(request: EmbeddingRequest):
    """
    Generate embeddings for a list of input texts.
    """
    try:
        embeddings = model.embed(request.texts)
        return EmbeddingResponse(embeddings=embeddings)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")
