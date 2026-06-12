"""Unit tests for the deduplication agent."""
import pytest
from app.agents.dedup_agent import _normalise_url, _tokenise, _jaccard


class TestNormaliseUrl:
    def test_strips_trailing_slash(self):
        assert _normalise_url("https://example.com/foo/") == "https://example.com/foo"

    def test_lowercases(self):
        assert _normalise_url("HTTPS://EXAMPLE.COM/PATH") == "https://example.com/path"

    def test_strips_fragment(self):
        result = _normalise_url("https://example.com/article#comments")
        assert "#comments" not in result

    def test_handles_bad_url(self):
        result = _normalise_url("not-a-url")
        assert isinstance(result, str)


class TestTokenise:
    def test_removes_stopwords(self):
        tokens = _tokenise("The new model is amazing")
        assert "the" not in tokens
        assert "is" not in tokens
        assert "model" in tokens
        assert "amazing" in tokens

    def test_lowercases(self):
        tokens = _tokenise("OpenAI Released GPT")
        assert "openai" in tokens

    def test_empty_string(self):
        assert _tokenise("") == set()


class TestJaccard:
    def test_identical_sets(self):
        s = {"a", "b", "c"}
        assert _jaccard(s, s) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        a = {"a", "b", "c"}
        b = {"b", "c", "d"}
        # intersection=2, union=4 → 0.5
        assert _jaccard(a, b) == pytest.approx(0.5)

    def test_empty_sets(self):
        assert _jaccard(set(), set()) == 0.0
