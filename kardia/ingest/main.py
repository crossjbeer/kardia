"""
Ingest files into the relational/vector database.

Supports: 
1. text
2. markdown 

Uses Llama-index for ETL and Embedding. 
"""

from __future__ import annotations

import os
from pathlib import Path

from kardia.config import Config
from kardia.ingest.config import IngestionConfig
from kardia.ingest.service import IngestionService

def main() -> None:
    config = IngestionConfig() 

    for path in Path(config.lore_dir).rglob("*"):
        print(path)
        if path.is_file():
            print(f" - {path}")

    service = IngestionService(config)
    service.ingest_directory(Path(config.lore_dir))


if __name__ == "__main__":
    main()