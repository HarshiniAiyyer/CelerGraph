# api/models.py

from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    message: Optional[str] = Field(default="", description="User question")
    conversation_id: Optional[str] = None
    max_tokens: int = 512
    temperature: float = 0.1
    bypass_cache: bool = False
    clear_cache: bool = False


class ChatResponse(BaseModel):
    answer: str
    references: List[str] = []


class IndexRequest(BaseModel):
    path: str = Field(..., description="Folder to index using chunker + chroma")
    rebuild: bool = False


class IndexResponse(BaseModel):
    indexed_files: List[str]
    chunks_processed: int


class HealthResponse(BaseModel):
    status: str = "ok"
    vector_db_status: str
    graph_status: str


class CacheResponse(BaseModel):
    status: str = "ok"
    cleared: bool = True
