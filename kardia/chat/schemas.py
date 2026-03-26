from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    chat_id: Optional[int] = Field(default=None, description="Existing chat to continue")
    message: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)
    model: str = Field(default="claude-sonnet-4-0")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


class SourceChunk(BaseModel):
    chunk_ids: Optional[list[int]] = None
    document_id: int
    filename: str
    filepath: str
    description: Optional[str] = None
    content: str
    similarity: float


class ChatResponse(BaseModel):
    chat_id: int
    answer: str
    retrieved_chunks: list[SourceChunk]