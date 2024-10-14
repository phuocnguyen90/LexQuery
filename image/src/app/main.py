from fastapi import FastAPI, Depends
from providers.groq_provider import GroqProvider
from rag_app.query_rag import query_rag

# Initialize FastAPI
app = FastAPI()

# Initialize GroqProvider at startup
groq_provider = GroqProvider(config={})

# Dependency for GroqProvider
def get_groq_provider():
    return groq_provider

@app.post("/submit_query")
async def submit_query(query_text: str, groq_provider=Depends(get_groq_provider)):
    response = query_rag(query_text, groq_provider)
    return {"response_text": response.response_text, "sources": response.sources}
