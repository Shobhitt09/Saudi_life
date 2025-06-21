from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    query: str
    name: Optional[str]
    request_id: Optional[str] = None

class IngestRequest(BaseModel):
    urls: Optional[list[str]] = None
    texts: Optional[list[str]] = None
    request_id: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    k: Optional[int] = 3
    request_id: Optional[str] = None

