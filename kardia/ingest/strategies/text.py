"""Ingestion strategy for text files. Splits into character-based chunks by default."""
from __future__ import annotations

from typing import List, Optional
from pathlib import Path

from kardia.ingest.strategies.base import BaseIngestionStrategy
from kardia.ingest.util import read_text_file, sha256_file
from kardia.ingest.payloads import PreparedDocument, PreparedChunk

class TextIngestionStrategy(BaseIngestionStrategy):
    def consume(self, path: Path, description: Optional[str] = None) -> PreparedDocument:
        raw_text = read_text_file(path)
        file_hash = sha256_file(path)

        llama_doc = self.etl.make_llama_doc(path, raw_text)
        nodes = self.etl.sentence_splitter.get_nodes_from_documents([llama_doc])

        texts = [node.get_content(metadata_mode="none") for node in nodes]
        embeddings = self.etl.embed_texts(texts)

        prepared_chunks: List[PreparedChunk] = []
        for node, embedding in zip(nodes, embeddings):
            content = node.get_content(metadata_mode="none")

            prepared_chunks.append(
                PreparedChunk(
                    content=content,
                    start_index=getattr(node, "start_char_idx", None),
                    end_index=getattr(node, "end_char_idx", None),
                    embedding=embedding,
                )
            )

        return PreparedDocument(
            filename=path.name,
            filepath=str(path.resolve()),
            file_hash=file_hash,
            description=description,
            chunks=prepared_chunks,
        )