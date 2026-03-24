from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kardia.db.models import Chunk, Document
from kardia.retrieval.schemas import RetrievalResult
from kardia.retrieval.strategies.base import BaseRetrievalStrategy


class KeywordSearchStrategy(BaseRetrievalStrategy):
    def retrieve(
        self,
        db: Session,
        query: str,
        k: int,
        scope: Optional[str] = None,
    ) -> List[RetrievalResult]:
        tsquery = func.plainto_tsquery("english", query)
        rank_expr = func.ts_rank(Chunk.search_vector, tsquery).label("rank")

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
                rank_expr,
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Chunk.search_vector.op("@@")(tsquery))
            .order_by(rank_expr.desc())
            .limit(k)
        )

        rows = db.execute(stmt).all()

        return [
            RetrievalResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                filename=row.filename,
                filepath=row.filepath,
                description=row.description,
                content=row.content,
                start_index=row.start_index,
                end_index=row.end_index,
                distance=1.0 - float(row.rank),
                similarity=float(row.rank),
            )
            for row in rows
        ]
