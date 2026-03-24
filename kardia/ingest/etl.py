from __future__ import annotations

from kardia.config import Config
from kardia.db.models import Base, Document, Chunk



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