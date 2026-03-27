"""
Patches heavy dependencies before any test module is collected or imported.

strategy_registry.py runs module-level code that instantiates LlamaIndexETL,
which calls HuggingFaceEmbedding() and would download/load the bge-small model.
Intercepting via sys.modules here prevents that from happening during test runs.
"""
import sys
from unittest.mock import MagicMock

_hf_module = MagicMock()
_hf_module.HuggingFaceEmbedding = MagicMock
sys.modules.setdefault("llama_index.embeddings.huggingface", _hf_module)
