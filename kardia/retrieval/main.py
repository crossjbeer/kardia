from __future__ import annotations

from kardia.retrieval.config import RetrievalConfig
from kardia.retrieval.service import RetrievalService

def main() -> None:
    config = RetrievalConfig()
    service = RetrievalService(config)

    query = "What are some locations in the environment?"
    response = service.retrieve(query, k=5)

    for r in response.results:
        print(f"[{r.similarity:.3f}] {r.filename} — {r.content[:80]}")


if __name__ == "__main__":
    main()
