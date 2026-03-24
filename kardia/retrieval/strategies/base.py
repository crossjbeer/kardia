from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from sqlalchemy.orm import Session

from kardia.retrieval.schemas import RetrievalResult


class BaseRetrievalStrategy(ABC):
    @abstractmethod
    def retrieve(
        self,
        db: Session,
        query: str,
        k: int,
        scope: Optional[str] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve the top-k most relevant chunks for a query.

        Args:
            db: Active SQLAlchemy session.
            query: Raw query string.
            k: Number of results to return.
            scope: Optional filter (e.g. corpus type) — reserved for future use.
        """
        raise NotImplementedError
