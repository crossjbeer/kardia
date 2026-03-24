from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from sqlalchemy import create_engine 
from sqlalchemy.orm import sessionmaker

from kardia.db.models import Base, Document 

from kardia.ingest.strategy_registry import ingestion_registry 
from kardia.ingest.config import IngestionConfig 
from kardia.ingest.persist import DocumentRepository

class IngestionService:
    def __init__(self, config: IngestionConfig) -> None:
        self.config = config

        engine = create_engine(config.database_url, future=True)
        Base.metadata.create_all(engine)
        self.SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

        self.registry = ingestion_registry

    def ingest_file(self, path: Path, description: Optional[str] = None) -> Optional[Document]:
        if not self.registry.supports(path.suffix):
            print(f"Skipping unsupported file: {path}")
            return None

        strategy = self.registry.get(path.suffix)
        prepared = strategy.consume(path, description=description)

        with self.SessionLocal() as session:
            repo = DocumentRepository(session)
            doc = repo.upsert_prepared_document(prepared)
            session.commit()
            return doc

    def ingest_directory(self, directory: Path) -> List[str]:
        ingested: List[str] = []

        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if not self.registry.supports(path.suffix):
                continue

            self.ingest_file(path)
            ingested.append(str(path))

        return ingested