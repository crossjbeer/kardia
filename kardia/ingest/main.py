"""Ingest text / markdown files into the relational/vector database using llama-index"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from llama_index.core.schema import Document as LlamaDocument
from llama_index.core.node_parser import SentenceSplitter, MarkdownNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# -------------------------------------------------------------------
# Your SQLAlchemy models
# -------------------------------------------------------------------
from kardia.db.models import Base, Document, Chunk  
from kardia.config import Config  

# -------------------------------------------------------------------
# Config
# -------------------------------------------------------------------

@dataclass(slots=True)
class IngestionConfig:
    database_url: str
    embedding_model_name: str = Config.EMBEDDING_MODEL
    chunk_size: int = 512
    chunk_overlap: int = 64
    lore_dir: str = Config.LORE_DIR


# -------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            h.update(block)
    return h.hexdigest()


def read_text_file(path: Path) -> str:
    # utf-8 first, then a permissive fallback
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


# -------------------------------------------------------------------
# ETL payload
# -------------------------------------------------------------------

@dataclass(slots=True)
class PreparedChunk:
    content: str
    start_index: Optional[int]
    end_index: Optional[int]
    embedding: List[float]


@dataclass(slots=True)
class PreparedDocument:
    filename: str
    filepath: str
    file_hash: str
    description: Optional[str]
    chunks: List[PreparedChunk]


# -------------------------------------------------------------------
# Shared LlamaIndex ETL helpers
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# Strategy base
# -------------------------------------------------------------------

class BaseIngestionStrategy(ABC):
    def __init__(self, etl: LlamaIndexETL) -> None:
        self.etl = etl

    @abstractmethod
    def consume(self, path: Path, description: Optional[str] = None) -> PreparedDocument:
        """
        Full ETL for a specific source type:
        extract -> transform/chunk -> embed -> return DB-ready payload
        """
        raise NotImplementedError


# -------------------------------------------------------------------
# TXT strategy
# -------------------------------------------------------------------

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

            print(prepared_chunks[-1])
            # input() 

        return PreparedDocument(
            filename=path.name,
            filepath=str(path.resolve()),
            file_hash=file_hash,
            description=description,
            chunks=prepared_chunks,
        )


# -------------------------------------------------------------------
# Markdown strategy
# -------------------------------------------------------------------

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

            refined = self.etl.sentence_splitter.get_nodes_from_documents(
                [
                    LlamaDocument(
                        text=content,
                        metadata={
                            **(md_node.metadata or {}),
                            "filename": path.name,
                            "filepath": str(path.resolve()),
                        },
                    )
                ]
            )
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


# -------------------------------------------------------------------
# Registry
# -------------------------------------------------------------------

class IngestionRegistry:
    def __init__(self) -> None:
        self._strategies: Dict[str, BaseIngestionStrategy] = {}

    def register(self, extension: str, strategy: BaseIngestionStrategy) -> None:
        self._strategies[extension.lower()] = strategy

    def get(self, extension: str) -> BaseIngestionStrategy:
        ext = extension.lower()
        if ext not in self._strategies:
            raise ValueError(f"No ingestion strategy registered for extension: {ext}")
        return self._strategies[ext]

    def supports(self, extension: str) -> bool:
        return extension.lower() in self._strategies


# -------------------------------------------------------------------
# Persistence layer
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# Orchestrator
# -------------------------------------------------------------------

class IngestionService:
    def __init__(self, config: IngestionConfig) -> None:
        self.config = config

        engine = create_engine(config.database_url, future=True)
        Base.metadata.create_all(engine)
        self.SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)

        etl = LlamaIndexETL(config)

        self.registry = IngestionRegistry()
        self.registry.register(".txt", TextIngestionStrategy(etl))
        self.registry.register(".md", MarkdownIngestionStrategy(etl))

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


# -------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------

def main() -> None:
    database_url = os.getenv("DATABASE_URL", Config.POSTGRES_URL)
    config = IngestionConfig(
        database_url=database_url,
        lore_dir=os.getenv("LORE_DIR", "./lore"),
        embedding_model_name=os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5"),
        chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "64")),
    )

    # print files avail: 
    print(f"Looking for files in: {config.lore_dir}")
    print("Current Dir: ", os.getcwd())
    for path in Path(config.lore_dir).rglob("*"):
        print(path)
        if path.is_file():
            print(f" - {path}")

    service = IngestionService(config)
    ingested = service.ingest_directory(Path(config.lore_dir))

    print("Ingested files:")
    for item in ingested:
        print(f" - {item}")


if __name__ == "__main__":
    main()