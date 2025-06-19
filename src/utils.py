from pydantic import BaseModel

class ChatRequest(BaseModel):
    name: str
    query: str