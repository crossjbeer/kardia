"""Handles pushing prepared documents and chunks to the database"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from kardia.ingest.payloads import PreparedDocument
from kardia.db.models import Document, Chunk

class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_prepared_document(self, prepared: PreparedDocument) -> Document:
        """
        Idempotent-ish behavior:
        - if filename exists and hash matches: skip re-ingest
        - if filename exists and hash differs: replace chunks + update metadata
        - else: insert new document and chunks
        """
        existing = self.session.execute(
            select(Document).where(Document.filename == prepared.filename)
        ).scalar_one_or_none()

        if existing and existing.file_hash == prepared.file_hash:
            return existing

        if existing is None:
            doc = Document(
                filename=prepared.filename,
                filepath=prepared.filepath,
                file_hash=prepared.file_hash,
                description=prepared.description,
            )
            self.session.add(doc)
            self.session.flush()  # get doc.id
        else:
            doc = existing
            doc.filepath = prepared.filepath
            doc.file_hash = prepared.file_hash
            doc.description = prepared.description

            # cascade delete-orphan handles chunk replacement once collection is reassigned
            doc.chunks.clear()
            self.session.flush()

        for ch in prepared.chunks:
            doc.chunks.append(
                Chunk(
                    content=ch.content,
                    start_index=ch.start_index,
                    end_index=ch.end_index,
                    embedding=ch.embedding,
                )
            )

        self.session.add(doc)
        return doc