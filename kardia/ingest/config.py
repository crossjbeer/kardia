# Config for easy access to common settings
from dataclasses import dataclass

from kardia.config import Config

@dataclass(slots=True)
class IngestionConfig:
    database_url: str = Config.POSTGRES_URL
    embedding_model_name: str = Config.EMBEDDING_MODEL
    chunk_size: int = Config.MAX_CHUNK_SIZE_CHARS
    chunk_overlap: int = Config.CHUNK_OVERLAP_CHARS
    lore_dir: str = Config.LORE_DIR