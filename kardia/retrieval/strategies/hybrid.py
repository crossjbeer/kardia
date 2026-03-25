from __future__ import annotations

from typing import Callable, Dict, List, Optional

from sqlalchemy.orm import Session

from kardia.retrieval.schemas import RetrievalResult
from kardia.retrieval.strategies.base import BaseRetrievalStrategy
from kardia.retrieval.strategies.keyword import KeywordSearchStrategy
from kardia.retrieval.strategies.vector import VectorSearchStrategy

_RRF_K = 60  # RRF constant — higher value reduces the impact of high rankings


class HybridSearchStrategy(BaseRetrievalStrategy):
    def __init__(self, embedder: Callable[[str], List[float]]) -> None:
        self._vector = VectorSearchStrategy(embedder)
        self._keyword = KeywordSearchStrategy()

    def retrieve(
        self,
        db: Session,
        query: str,
        k: int,
        scope: Optional[str] = None,
    ) -> List[RetrievalResult]:
        fetch_k = k * 3  # over-fetch so fusion has enough candidates

        vector_results = self._vector.retrieve(db, query, fetch_k, scope)
        # print(f"len(vector_results) = {len(vector_results)}")
        keyword_results = self._keyword.retrieve(db, query, fetch_k, scope)
        # print(f"len(keyword_results) = {len(keyword_results)}")

        # RRF score: sum of 1 / (rank + K) across each ranked list
        rrf_scores: Dict[int, float] = {}
        best_result: Dict[int, RetrievalResult] = {}

        for rank, result in enumerate(vector_results):
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0.0) + 1.0 / (rank + 1 + _RRF_K)
            best_result[result.chunk_id] = result

        for rank, result in enumerate(keyword_results):
            rrf_scores[result.chunk_id] = rrf_scores.get(result.chunk_id, 0.0) + 1.0 / (rank + 1 + _RRF_K)
            if result.chunk_id not in best_result:
                best_result[result.chunk_id] = result

        ranked = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:k]

        return [
            RetrievalResult(
                **best_result[chunk_id].model_dump(exclude={"similarity", "distance"}),
                similarity=score,
                distance=1.0 - score,
            )
            for chunk_id, score in ranked
        ]
