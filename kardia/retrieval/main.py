from __future__ import annotations

from dataclasses import dataclass
from typing import Generator, List, Optional

from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from kardia.config import Config
from kardia.db.models import Chunk, Document


# --------------------------------------------------
# Config
# --------------------------------------------------

@dataclass(slots=True)
class RetrievalConfig:
    database_url: str
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"


config = RetrievalConfig(
    database_url=Config.POSTGRES_URL,
    embedding_model_name=Config.EMBEDDING_MODEL,
)


# --------------------------------------------------
# Database
# --------------------------------------------------

engine = create_engine(config.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------
# Embedder
# --------------------------------------------------

# Load once at process startup
embed_model = HuggingFaceEmbedding(model_name=config.embedding_model_name)


def embed_query(text: str) -> List[float]:
    text = text.strip()
    if not text:
        raise ValueError("Query cannot be empty.")
    return embed_model.get_query_embedding(text)


# --------------------------------------------------
# API schemas
# --------------------------------------------------

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


# --------------------------------------------------
# Retrieval service
# --------------------------------------------------

def retrieve_knn(db: Session, query_text: str, k: int = 5) -> RetrievalResponse:
    query_embedding = embed_query(query_text)

    # pgvector cosine distance:
    # lower distance = more similar
    distance_expr = Chunk.embedding.cosine_distance(query_embedding).label("distance")

    stmt = (
        select(
            Chunk.id.label("chunk_id"),
            Chunk.document_id.label("document_id"),
            Document.filename.label("filename"),
            Document.filepath.label("filepath"),
            Document.description.label("description"),
            Chunk.content.label("content"),
            Chunk.start_index.label("start_index"),
            Chunk.end_index.label("end_index"),
            distance_expr,
        )
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.embedding.is_not(None))
        .order_by(distance_expr.asc())
        .limit(k)
    )

    rows = db.execute(stmt).all()

    results = []
    for row in rows:
        distance = float(row.distance)
        similarity = 1.0 - distance  # convenient if using cosine distance

        results.append(
            RetrievalResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                filename=row.filename,
                filepath=row.filepath,
                description=row.description,
                content=row.content,
                start_index=row.start_index,
                end_index=row.end_index,
                distance=distance,
                similarity=similarity,
            )
        )

    return RetrievalResponse(query=query_text, k=k, results=results)

# --------------------------------------------------

def main() -> None: 
    # Example usage
    with SessionLocal() as db:
        query = "What are some locations in the environment?"
        response = retrieve_knn(db, query, k=5)

if __name__ == "__main__":
    main()