# ETL payload
from dataclasses import dataclass
from typing import List, Optional


@dataclass(slots=True)
class PreparedChunk:
    content: str
    start_index: Optional[int]
    end_index: Optional[int]
    embedding: List[float]


@dataclass(slots=True)
class PreparedDocument:
    filename: str
    filepath: str
    file_hash: str
    description: Optional[str]
    chunks: List[PreparedChunk]