"""Ingest text / markdown files into the relational/vector database using llama-index"""

from __future__ import annotations

import os
from pathlib import Path

from kardia.config import Config
from kardia.ingest.config import IngestionConfig
from kardia.ingest.service import IngestionService

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