from pydantic import BaseModel

class SubmitQueryRequest(BaseModel):
    query_text: str
