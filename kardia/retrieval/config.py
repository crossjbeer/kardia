from dataclasses import dataclass

from kardia.config import Config

@dataclass(slots=True)
class RetrievalConfig:
    database_url: str = Config.POSTGRES_URL
    embedding_model_name: str = Config.EMBEDDING_MODEL

