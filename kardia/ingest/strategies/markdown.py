from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from kardia.ingest.strategies.base import BaseIngestionStrategy
from kardia.ingest.util import read_text_file, sha256_file
from kardia.ingest.payloads import PreparedChunk, PreparedDocument

class MarkdownIngestionStrategy(BaseIngestionStrategy):
    def consume(self, path: Path, description: Optional[str] = None) -> PreparedDocument:
        raw_text = read_text_file(path)
        file_hash = sha256_file(path)

        llama_doc = self.etl.make_llama_doc(path, raw_text)

        # First split by markdown structure
        md_nodes = self.etl.markdown_parser.get_nodes_from_documents([llama_doc])

        # Then optionally refine large markdown sections into sentence-based chunks
        final_nodes = []
        for md_node in md_nodes:
            content = md_node.get_content(metadata_mode="none")
            if len(content) <= self.etl.config.chunk_size:
                final_nodes.append(md_node)
                continue

            refined = self.etl.sentence_splitter.get_nodes_from_documents([self.etl.make_llama_doc(path, content)])

            final_nodes.extend(refined)

        texts = [node.get_content(metadata_mode="none") for node in final_nodes]
        embeddings = self.etl.embed_texts(texts)

        prepared_chunks: List[PreparedChunk] = []

        for node, embedding in zip(final_nodes, embeddings):
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