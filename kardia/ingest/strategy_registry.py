from __future__ import annotations

from typing import Dict

from kardia.ingest.strategies.base import BaseIngestionStrategy

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
