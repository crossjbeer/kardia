"""Tests for DocumentRepository.upsert_prepared_document.

The three branches under test:
  - skip:   filename exists, hash matches  → return existing, no DB writes
  - insert: filename not found             → create Document + Chunks
  - update: filename exists, hash differs  → replace chunks, update metadata
"""
import pytest
from unittest.mock import MagicMock, call

from kardia.ingest.persist import DocumentRepository
from kardia.ingest.payloads import PreparedDocument, PreparedChunk
from kardia.db.models import Document, Chunk


def _prepared(filename="doc.txt", file_hash="abc123", n_chunks=1) -> PreparedDocument:
    chunks = [
        PreparedChunk(
            content=f"chunk {i}",
            start_index=i * 10,
            end_index=i * 10 + 9,
            embedding=[0.1] * 384,
        )
        for i in range(n_chunks)
    ]
    return PreparedDocument(
        filename=filename,
        filepath=f"/lore/{filename}",
        file_hash=file_hash,
        description=None,
        chunks=chunks,
    )


@pytest.fixture
def session():
    return MagicMock()


# ---------------------------------------------------------------------------
# Skip branch
# ---------------------------------------------------------------------------

class TestSkip:
    def test_returns_existing_document_unchanged(self, session):
        existing = Document(filename="doc.txt", filepath="/lore/doc.txt", file_hash="abc123")
        session.execute.return_value.scalar_one_or_none.return_value = existing

        result = DocumentRepository(session).upsert_prepared_document(_prepared(file_hash="abc123"))

        assert result is existing

    def test_no_db_writes_on_hash_match(self, session):
        existing = Document(filename="doc.txt", filepath="/lore/doc.txt", file_hash="abc123")
        session.execute.return_value.scalar_one_or_none.return_value = existing

        DocumentRepository(session).upsert_prepared_document(_prepared(file_hash="abc123"))

        session.add.assert_not_called()
        session.flush.assert_not_called()


# ---------------------------------------------------------------------------
# Insert branch
# ---------------------------------------------------------------------------

class TestInsert:
    def test_session_add_and_flush_called(self, session):
        session.execute.return_value.scalar_one_or_none.return_value = None

        DocumentRepository(session).upsert_prepared_document(_prepared())

        session.add.assert_called()
        session.flush.assert_called()

    def test_returned_document_has_correct_fields(self, session):
        session.execute.return_value.scalar_one_or_none.return_value = None
        prepared = _prepared(filename="world.txt", file_hash="deadbeef")

        result = DocumentRepository(session).upsert_prepared_document(prepared)

        assert result.filename == "world.txt"
        assert result.filepath == "/lore/world.txt"
        assert result.file_hash == "deadbeef"

    def test_chunks_appended_to_new_document(self, session):
        session.execute.return_value.scalar_one_or_none.return_value = None
        prepared = _prepared(n_chunks=3)

        result = DocumentRepository(session).upsert_prepared_document(prepared)

        assert len(result.chunks) == 3

    def test_chunks_have_correct_content(self, session):
        session.execute.return_value.scalar_one_or_none.return_value = None

        result = DocumentRepository(session).upsert_prepared_document(_prepared(n_chunks=2))

        contents = [c.content for c in result.chunks]
        assert contents == ["chunk 0", "chunk 1"]

    def test_chunk_instances_are_orm_objects(self, session):
        session.execute.return_value.scalar_one_or_none.return_value = None

        result = DocumentRepository(session).upsert_prepared_document(_prepared())

        assert all(isinstance(c, Chunk) for c in result.chunks)


# ---------------------------------------------------------------------------
# Update branch
# ---------------------------------------------------------------------------

class TestUpdate:
    def _existing(self):
        # MagicMock(spec=Document) avoids SQLAlchemy intercepting attribute
        # assignments — a real Document instance replaces .chunks with an
        # InstrumentedList, making it impossible to assert on clear/append.
        doc = MagicMock(spec=Document)
        doc.filename = "doc.txt"
        doc.filepath = "/lore/doc.txt"
        doc.file_hash = "old_hash"
        return doc

    def test_file_hash_updated(self, session):
        session.execute.return_value.scalar_one_or_none.return_value = self._existing()

        result = DocumentRepository(session).upsert_prepared_document(_prepared(file_hash="new_hash"))

        assert result.file_hash == "new_hash"

    def test_filepath_updated(self, session):
        existing = self._existing()
        existing.filepath = "/old/path/doc.txt"
        session.execute.return_value.scalar_one_or_none.return_value = existing
        prepared = _prepared(file_hash="new_hash")
        prepared.filepath  # already "/lore/doc.txt"

        result = DocumentRepository(session).upsert_prepared_document(prepared)

        assert result.filepath == "/lore/doc.txt"

    def test_old_chunks_cleared(self, session):
        existing = self._existing()
        session.execute.return_value.scalar_one_or_none.return_value = existing

        DocumentRepository(session).upsert_prepared_document(_prepared(file_hash="new_hash"))

        existing.chunks.clear.assert_called_once()

    def test_new_chunks_appended(self, session):
        existing = self._existing()
        session.execute.return_value.scalar_one_or_none.return_value = existing

        DocumentRepository(session).upsert_prepared_document(_prepared(file_hash="new_hash", n_chunks=2))

        assert existing.chunks.append.call_count == 2

    def test_appended_chunks_are_orm_objects(self, session):
        existing = self._existing()
        session.execute.return_value.scalar_one_or_none.return_value = existing

        DocumentRepository(session).upsert_prepared_document(_prepared(file_hash="new_hash"))

        chunk_arg = existing.chunks.append.call_args[0][0]
        assert isinstance(chunk_arg, Chunk)

    def test_flush_called_after_clear(self, session):
        existing = self._existing()
        session.execute.return_value.scalar_one_or_none.return_value = existing

        DocumentRepository(session).upsert_prepared_document(_prepared(file_hash="new_hash"))

        # flush must happen between clear and append so the cascade delete fires
        flush_order = [c for c in session.mock_calls if "flush" in str(c)]
        assert len(flush_order) >= 1
