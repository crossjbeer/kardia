"""Registers and manages retrieval strategies for different retrieval modes."""
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

from kardia.retrieval.strategies.vector import VectorSearchStrategy
from kardia.retrieval.strategies.keyword import KeywordSearchStrategy
from kardia.retrieval.strategies.hybrid import HybridSearchStrategy
from kardia.retrieval.embedder import embed_query

retrieval_registry = RetrievalRegistry()
retrieval_registry.register("vector", VectorSearchStrategy(embed_query))
retrieval_registry.register("keyword", KeywordSearchStrategy())
retrieval_registry.register("hybrid", HybridSearchStrategy(embed_query))
