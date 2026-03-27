"""Tests for IngestionRegistry."""
import pytest
from unittest.mock import MagicMock

from kardia.ingest.strategy_registry import IngestionRegistry


@pytest.fixture
def registry():
    return IngestionRegistry()


@pytest.fixture
def strategy():
    return MagicMock()


class TestIngestionRegistry:
    def test_register_and_get(self, registry, strategy):
        registry.register(".txt", strategy)

        assert registry.get(".txt") is strategy

    def test_get_normalizes_extension_to_lowercase(self, registry, strategy):
        registry.register(".txt", strategy)

        assert registry.get(".TXT") is strategy

    def test_register_normalizes_extension_to_lowercase(self, registry, strategy):
        registry.register(".MD", strategy)

        assert registry.get(".md") is strategy

    def test_supports_returns_true_for_registered(self, registry, strategy):
        registry.register(".txt", strategy)

        assert registry.supports(".txt") is True

    def test_supports_returns_false_for_unregistered(self, registry):
        assert registry.supports(".pdf") is False

    def test_get_raises_for_unknown_extension(self, registry):
        with pytest.raises(ValueError, match=".pdf"):
            registry.get(".pdf")

    def test_register_overwrites_existing_strategy(self, registry):
        s1, s2 = MagicMock(), MagicMock()
        registry.register(".txt", s1)
        registry.register(".txt", s2)

        assert registry.get(".txt") is s2

    def test_multiple_extensions_registered_independently(self, registry):
        s_txt, s_md = MagicMock(), MagicMock()
        registry.register(".txt", s_txt)
        registry.register(".md", s_md)

        assert registry.get(".txt") is s_txt
        assert registry.get(".md") is s_md
