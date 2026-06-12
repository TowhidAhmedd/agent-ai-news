"""Unit tests for Pydantic models."""
import pytest
from datetime import datetime, timezone
from app.models.article import (
    RawArticle,
    ScoredArticle,
    SummarizedArticle,
    RankedArticle,
    AgentState,
)


class TestRawArticle:
    def test_basic_creation(self):
        art = RawArticle(
            url="https://openai.com/blog/gpt5",
            title="GPT-5 Released",
            source_name="OpenAI Blog",
            feed_url="https://openai.com/blog/rss.xml",
        )
        assert art.title == "GPT-5 Released"
        assert art.author is None

    def test_full_creation(self):
        art = RawArticle(
            url="https://example.com",
            title="Test",
            source_name="Test Source",
            feed_url="https://example.com/rss",
            published_at=datetime.now(timezone.utc),
            author="Jane Doe",
            summary="Summary text",
            full_text="Full article text here",
        )
        assert art.author == "Jane Doe"


class TestScoredArticle:
    def test_inherits_raw(self):
        art = ScoredArticle(
            url="https://example.com",
            title="Test",
            source_name="Test",
            feed_url="https://example.com/rss",
            relevance_score=75.0,
        )
        assert art.relevance_score == 75.0
        assert art.score_breakdown == {}


class TestAgentState:
    def test_default_state(self):
        state = AgentState(run_id="test-run-001")
        assert state.raw_articles == []
        assert state.email_sent is False
        assert state.total_articles_discovered == 0

    def test_state_with_articles(self):
        art = RawArticle(
            url="https://example.com",
            title="Test",
            source_name="Test",
            feed_url="https://example.com/rss",
        )
        state = AgentState(run_id="test-run-002", raw_articles=[art])
        assert len(state.raw_articles) == 1
