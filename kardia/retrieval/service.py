from __future__ import annotations

from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from kardia.retrieval.config import RetrievalConfig
from kardia.retrieval.schemas import RetrievalResponse
from kardia.retrieval.strategy_registry import retrieval_registry


class RetrievalService:
    def __init__(self, config: RetrievalConfig) -> None:
        self.config = config

        engine = create_engine(config.database_url, future=True)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

        self.registry = retrieval_registry

    def retrieve(
        self,
        query: str,
        k: int = 5,
        mode: str = "vector",
        scope: Optional[str] = None,
    ) -> RetrievalResponse:
        strategy = self.registry.get(mode)

        with self.SessionLocal() as db:
            results = strategy.retrieve(db, query, k, scope=scope)

        return RetrievalResponse(query=query, k=k, results=results)
