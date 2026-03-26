"""Centralized config that pulls from our environment. Includes sane defaults if something gets messed up."""
import os 

class Config:
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER", "kardia")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "kardia")
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB", "kardia")
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.environ.get("POSTGRES_PORT", "5432")

    POSTGRES_URL: str = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    LORE_DIR: str = os.environ.get("LORE_DIR", "./lore")

    MAX_CHUNK_SIZE_CHARS: int = int(os.environ.get("MAX_CHUNK_SIZE_CHARS", "512"))
    CHUNK_OVERLAP_CHARS: int = int(os.environ.get("CHUNK_OVERLAP_CHARS", "64"))
    EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    LLM_MODEL: str = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")
    LLM_TEMPERATURE: float = float(os.environ.get("LLM_TEMPERATURE", "0.2"))

    