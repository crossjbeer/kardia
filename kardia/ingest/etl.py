from __future__ import annotations

from pathlib import Path
from typing import List

from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import Document as LlamaDocument
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from kardia.ingest.config import IngestionConfig

# Shared LlamaIndex ETL helpers
class LlamaIndexETL:
    """
    Shared LlamaIndex tooling used by all strategies.
    """

    def __init__(self, config: IngestionConfig) -> None:
        self.config = config
        self.embed_model = HuggingFaceEmbedding(model_name=config.embedding_model_name)
        self.sentence_splitter = SentenceSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            tokenizer=list,  # list("text") splits to chars, so chunk_size is in characters NOTE: may want to switch to a token-based splitter in the future. Currently limited by our embedding model, bge-small
        )
        self.markdown_parser = MarkdownNodeParser()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Batch embedding keeps this reasonably efficient.
        """
        return self.embed_model.get_text_embedding_batch(texts)

    def make_llama_doc(self, path: Path, text: str) -> LlamaDocument:
        return LlamaDocument(
            text=text,
            metadata={
                "filename": path.name,
                "filepath": str(path.resolve()),
                "extension": path.suffix.lower(),
            },
        )