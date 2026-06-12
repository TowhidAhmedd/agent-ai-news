"""
Integration tests for the discovery agent.
These make real HTTP calls — mark with pytest.mark.integration.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.article import AgentState, RawArticle
from app.agents.discovery_agent import discovery_node, _fetch_feed


@pytest.fixture
def empty_state():
    return AgentState(run_id="test-integration-001")


class TestDiscoveryNode:
    @pytest.mark.asyncio
    async def test_discovery_node_runs(self, empty_state):
        """Discovery node executes and updates state."""
        # Mock the HTTP client to avoid real network calls
        mock_article = RawArticle(
            url="https://example.com/article",
            title="Test AI Article",
            source_name="Test Feed",
            feed_url="https://example.com/rss",
            summary="This is a test article about AI.",
        )

        with patch("app.agents.discovery_agent._fetch_feed", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = ([mock_article], [])
            result = await discovery_node(empty_state)

        assert isinstance(result, AgentState)
        assert result.total_articles_discovered > 0
        assert len(result.raw_articles) > 0
        assert "discovery" in result.node_timings

    @pytest.mark.asyncio
    async def test_discovery_handles_feed_error(self, empty_state):
        """Discovery node continues even if feeds fail."""
        with patch("app.agents.discovery_agent._fetch_feed", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")
            result = await discovery_node(empty_state)

        assert isinstance(result, AgentState)
        # Should not crash; errors captured
        assert len(result.discovery_errors) > 0


class TestDeduplication:
    @pytest.mark.asyncio
    async def test_removes_duplicates(self):
        from app.agents.dedup_agent import dedup_node

        articles_data = [
            {"url": "https://example.com/a", "title": "OpenAI launches GPT-5 model today"},
            {"url": "https://example.com/b", "title": "OpenAI launches GPT-5 model today"},  # dup
            {"url": "https://example.com/c", "title": "Google releases Gemini Ultra 2"},
        ]

        from app.models.article import ScoredArticle
        articles = [
            ScoredArticle(
                url=a["url"],
                title=a["title"],
                source_name="Test",
                feed_url="https://example.com/rss",
                relevance_score=75.0,
            )
            for a in articles_data
        ]

        state = AgentState(run_id="test-dedup", scored_articles=articles)
        result = await dedup_node(state)

        # Should have removed the near-duplicate
        assert len(result.deduplicated_articles) < len(articles)
