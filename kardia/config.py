import os 
from dataclasses import dataclass

@dataclass(slots=True)
class Config:
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER", "kardia")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "kardia")
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB", "kardia")
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST", "db")
    POSTGRES_PORT: str = os.environ.get("POSTGRES_PORT", "5432")

    POSTGRES_URL: str = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    EMBEDDING_MODEL: str = os.environ.get("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    LORE_DIR: str = os.environ.get("LORE_DIR", "./lore")

    LLM_MODEL: str = os.environ.get("LLM_MODEL", "claude-sonnet-4-6")
    LLM_TEMPERATURE: float = float(os.environ.get("LLM_TEMPERATURE", "0.2"))

    