from fastapi import APIRouter, HTTPException
from ..models import SubmitQueryRequest
from ..workers import invoke_worker_sync
from ..db.dynamodb_handler import save_query_item, get_query_item

router = APIRouter()

@router.post("/submit_query")
async def submit_query_endpoint(request: SubmitQueryRequest):
    new_query = save_query_item(request.query_text)
    
    # Invoke worker for RAG processing
    try:
        response = invoke_worker_sync(new_query)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail="Worker invocation failed.")

@router.get("/get_query")
async def get_query_endpoint(query_id: str):
    query = get_query_item(query_id)
    if query:
        return query
    raise HTTPException(status_code=404, detail="Query not found")
