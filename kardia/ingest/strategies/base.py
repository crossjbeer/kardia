
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from kardia.ingest.etl import LlamaIndexETL
from kardia.ingest.payloads import PreparedDocument

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