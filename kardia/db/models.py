from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

Base = declarative_base()

# documents — one row per file in lore/
class Document(Base):
    __tablename__ = "documents"

    id          = Column(Integer, primary_key=True)
    filename    = Column(String, nullable=False, unique=True)
    filepath    = Column(String, nullable=False)
    file_hash   = Column(String, nullable=False)   # sha256, for idempotent re-ingest
    description = Column(String, nullable=True)    # optional user-supplied metadata
    corpus      = Column(String, nullable=True)    # e.g. "lore", "house_rule", "official_rule", "supplement"
    campaign    = Column(String, nullable=True)    # which campaign/world this belongs to
    tags        = Column(String, nullable=True)    # comma-separated tags e.g. "combat,magic,underdark"
    game_system = Column(String, nullable=True)    # e.g. "dnd5e", "pathfinder2e", "custom"
    author      = Column(String, nullable=True)    # who wrote the document
    created_at  = Column(DateTime, server_default=func.now())

    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


# chunks — one row per text window from a document
class Chunk(Base):
    __tablename__ = "chunks"

    id          = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    content     = Column(Text, nullable=False)
    start_index = Column(Integer)
    end_index   = Column(Integer)
    embedding   = Column(Vector(384))             # ← must match bge-small dimension

    search_vector = Column(TSVECTOR) 

    document = relationship("Document", back_populates="chunks")

# chats — a conversation session
class Chat(Base):
    __tablename__ = "chats"

    id         = Column(Integer, primary_key=True)
    created_at = Column(DateTime, server_default=func.now())

    messages = relationship("ChatMessage", back_populates="chat", order_by="ChatMessage.id")


# chat_messages — individual turns
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True)
    chat_id    = Column(Integer, ForeignKey("chats.id"), nullable=False)
    role       = Column(String, nullable=False)   # "user" | "assistant"
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    chat = relationship("Chat", back_populates="messages")