from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class RetrievalResult(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    filepath: str
    description: Optional[str] = None
    content: str
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    distance: float
    similarity: float


class RetrievalResponse(BaseModel):
    query: str
    k: int
    results: List[RetrievalResult]
