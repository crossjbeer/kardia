from __future__ import annotations

from typing import Callable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from kardia.db.models import Chunk, Document
from kardia.retrieval.schemas import RetrievalResult
from kardia.retrieval.strategies.base import BaseRetrievalStrategy


class VectorSearchStrategy(BaseRetrievalStrategy):
    def __init__(self, embedder: Callable[[str], List[float]]) -> None:
        self._embed = embedder

    def retrieve(
        self,
        db: Session,
        query: str,
        k: int,
        scope: Optional[str] = None,
    ) -> List[RetrievalResult]:
        query_embedding = self._embed(query)

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
                    similarity=1.0 - distance,
                )
            )

        return results
