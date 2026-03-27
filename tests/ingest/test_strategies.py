"""Tests for TextIngestionStrategy and MarkdownIngestionStrategy."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from kardia.ingest.strategies.text import TextIngestionStrategy
from kardia.ingest.strategies.markdown import MarkdownIngestionStrategy
from kardia.ingest.payloads import PreparedDocument


def _make_node(content: str, start: int = 0, end: int = 10) -> MagicMock:
    node = MagicMock()
    node.get_content.return_value = content
    node.start_char_idx = start
    node.end_char_idx = end
    return node


@pytest.fixture
def mock_etl():
    etl = MagicMock()
    etl.config.chunk_size = 512
    etl.embed_texts.side_effect = lambda texts: [[0.1] * 384 for _ in texts]
    etl.make_llama_doc.side_effect = lambda path, text: MagicMock(text=text)
    return etl


# ---------------------------------------------------------------------------
# TextIngestionStrategy
# ---------------------------------------------------------------------------

class TestTextIngestionStrategy:
    def test_returns_prepared_document(self, mock_etl, tmp_path):
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [
            _make_node("chunk one", 0, 9),
            _make_node("chunk two", 10, 19),
        ]
        f = tmp_path / "test.txt"
        f.write_text("chunk one chunk two")

        result = TextIngestionStrategy(mock_etl).consume(f)

        assert isinstance(result, PreparedDocument)
        assert result.filename == "test.txt"
        assert result.filepath == str(f.resolve())
        assert len(result.chunks) == 2

    def test_chunk_embeddings_have_correct_dimension(self, mock_etl, tmp_path):
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [
            _make_node("some text"),
        ]
        f = tmp_path / "test.txt"
        f.write_text("some text")

        result = TextIngestionStrategy(mock_etl).consume(f)

        assert len(result.chunks[0].embedding) == 384

    def test_description_is_passed_through(self, mock_etl, tmp_path):
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [_make_node("x")]
        f = tmp_path / "test.txt"
        f.write_text("x")

        result = TextIngestionStrategy(mock_etl).consume(f, description="My notes")

        assert result.description == "My notes"

    def test_file_hash_is_deterministic(self, mock_etl, tmp_path):
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [_make_node("x")]
        f = tmp_path / "test.txt"
        f.write_text("hello world")

        r1 = TextIngestionStrategy(mock_etl).consume(f)
        r2 = TextIngestionStrategy(mock_etl).consume(f)

        assert r1.file_hash == r2.file_hash

    def test_file_hash_is_sha256_hex(self, mock_etl, tmp_path):
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [_make_node("x")]
        f = tmp_path / "test.txt"
        f.write_text("hello world")

        result = TextIngestionStrategy(mock_etl).consume(f)

        assert len(result.file_hash) == 64
        assert all(c in "0123456789abcdef" for c in result.file_hash)

    def test_embed_texts_called_with_all_chunk_contents(self, mock_etl, tmp_path):
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [
            _make_node("alpha"),
            _make_node("beta"),
        ]
        f = tmp_path / "test.txt"
        f.write_text("alpha beta")

        TextIngestionStrategy(mock_etl).consume(f)

        mock_etl.embed_texts.assert_called_once_with(["alpha", "beta"])

    def test_chunk_indices_come_from_nodes(self, mock_etl, tmp_path):
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [
            _make_node("content", start=5, end=12),
        ]
        f = tmp_path / "test.txt"
        f.write_text("content")

        result = TextIngestionStrategy(mock_etl).consume(f)

        assert result.chunks[0].start_index == 5
        assert result.chunks[0].end_index == 12


# ---------------------------------------------------------------------------
# MarkdownIngestionStrategy
# ---------------------------------------------------------------------------

class TestMarkdownIngestionStrategy:
    def test_small_sections_are_not_re_split(self, mock_etl, tmp_path):
        # Content length <= chunk_size (512) — should stay as a single node
        mock_etl.markdown_parser.get_nodes_from_documents.return_value = [
            _make_node("# Header\nshort content"),
        ]
        f = tmp_path / "notes.md"
        f.write_text("# Header\nshort content")

        result = MarkdownIngestionStrategy(mock_etl).consume(f)

        assert len(result.chunks) == 1
        mock_etl.sentence_splitter.get_nodes_from_documents.assert_not_called()

    def test_large_sections_are_re_split(self, mock_etl, tmp_path):
        long_content = "x" * 1000  # exceeds chunk_size of 512
        mock_etl.markdown_parser.get_nodes_from_documents.return_value = [
            _make_node(long_content),
        ]
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [
            _make_node("part one"),
            _make_node("part two"),
        ]
        f = tmp_path / "notes.md"
        f.write_text(long_content)

        result = MarkdownIngestionStrategy(mock_etl).consume(f)

        assert len(result.chunks) == 2
        mock_etl.sentence_splitter.get_nodes_from_documents.assert_called_once()

    def test_mixed_sections_combined_correctly(self, mock_etl, tmp_path):
        # One small section kept as-is, one large section split into two
        mock_etl.markdown_parser.get_nodes_from_documents.return_value = [
            _make_node("short"),
            _make_node("x" * 1000),
        ]
        mock_etl.sentence_splitter.get_nodes_from_documents.return_value = [
            _make_node("sub one"),
            _make_node("sub two"),
        ]
        f = tmp_path / "notes.md"
        f.write_text("short\n" + "x" * 1000)

        result = MarkdownIngestionStrategy(mock_etl).consume(f)

        assert len(result.chunks) == 3  # 1 small + 2 from re-split

    def test_returns_correct_filename_and_description(self, mock_etl, tmp_path):
        mock_etl.markdown_parser.get_nodes_from_documents.return_value = [
            _make_node("content"),
        ]
        f = tmp_path / "lore.md"
        f.write_text("content")

        result = MarkdownIngestionStrategy(mock_etl).consume(f, description="World lore")

        assert result.filename == "lore.md"
        assert result.description == "World lore"

    def test_chunk_embeddings_have_correct_dimension(self, mock_etl, tmp_path):
        mock_etl.markdown_parser.get_nodes_from_documents.return_value = [
            _make_node("content"),
        ]
        f = tmp_path / "notes.md"
        f.write_text("content")

        result = MarkdownIngestionStrategy(mock_etl).consume(f)

        assert len(result.chunks[0].embedding) == 384
