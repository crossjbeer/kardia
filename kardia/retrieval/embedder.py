"""Tiny embedding interface. May want to move this to a dedicated module if we add more embedding-related functionality."""

from __future__ import annotations

from typing import List

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from kardia.retrieval.config import RetrievalConfig

_config = RetrievalConfig()
_model = HuggingFaceEmbedding(model_name=_config.embedding_model_name)

def embed_query(text: str) -> List[float]:
    text = text.strip()
    if not text:
        raise ValueError("Query cannot be empty.")
    return _model.get_query_embedding(text)
