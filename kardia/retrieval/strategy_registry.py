from __future__ import annotations

from typing import Dict

from kardia.retrieval.strategies.base import BaseRetrievalStrategy


class RetrievalRegistry:
    def __init__(self) -> None:
        self._strategies: Dict[str, BaseRetrievalStrategy] = {}

    def register(self, mode: str, strategy: BaseRetrievalStrategy) -> None:
        self._strategies[mode.lower()] = strategy

    def get(self, mode: str) -> BaseRetrievalStrategy:
        key = mode.lower()
        if key not in self._strategies:
            raise ValueError(f"No retrieval strategy registered for mode: {key!r}")
        return self._strategies[key]

    def supports(self, mode: str) -> bool:
        return mode.lower() in self._strategies
