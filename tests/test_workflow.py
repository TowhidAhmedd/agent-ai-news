"""
Workflow test — verifies the full LangGraph pipeline runs end-to-end
using mocked LLM and HTTP calls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage

from app.models.article import (
    AgentState,
    RawArticle,
    ScoredArticle,
    SummarizedArticle,
    RankedArticle,
)


MOCK_SCORE_RESPONSE = '[{"index": 0, "score": 80, "category": "Model Release", "reason": "Important LLM release"}]'
MOCK_SUMMARY_RESPONSE = '{"executive_summary": "A major AI release.", "key_takeaways": ["Fast", "Cheap", "Good"], "why_it_matters": "Changes the industry.", "category": "Model Release"}'
MOCK_TRENDS_RESPONSE = '{"quick_trends": ["LLMs getting faster"], "market_signals": ["$1B raised"], "research_highlights": ["New paper on transformers"]}'


def make_mock_llm(response_text: str):
    llm = MagicMock()
    llm.ainvoke = AsyncMock(return_value=AIMessage(content=response_text))
    return llm


@pytest.mark.asyncio
async def test_dedup_node_standalone():
    """Dedup node correctly deduplicates articles."""
    from app.agents.dedup_agent import dedup_node

    articles = [
        ScoredArticle(url="https://a.com/1", title="New Model From OpenAI", source_name="S", feed_url="f", relevance_score=80),
        ScoredArticle(url="https://a.com/2", title="New Model From OpenAI", source_name="S", feed_url="f", relevance_score=75),  # near-dup
        ScoredArticle(url="https://b.com/1", title="Google Releases Gemini Ultra", source_name="S", feed_url="f", relevance_score=85),
    ]
    state = AgentState(run_id="test-wf-dedup", scored_articles=articles)
    result = await dedup_node(state)
    # Near-duplicate should be removed
    assert len(result.deduplicated_articles) == 2


@pytest.mark.asyncio
async def test_ranking_node_selects_top_n():
    """Ranking node selects top N articles by composite score."""
    from app.agents.ranking_agent import ranking_node

    articles = [
        SummarizedArticle(
            url=f"https://example.com/{i}",
            title=f"Article {i}",
            source_name="S",
            feed_url="f",
            relevance_score=float(i * 10),
            category="General",
        )
        for i in range(1, 15)
    ]

    state = AgentState(run_id="test-wf-rank", summarized_articles=articles)

    with patch("app.agents.ranking_agent.get_llm") as mock_factory:
        mock_factory.return_value = make_mock_llm(MOCK_TRENDS_RESPONSE)
        result = await ranking_node(state)

    assert len(result.ranked_articles) <= 10
    assert result.ranked_articles[0].rank == 1
    # Top article should have highest score
    assert result.ranked_articles[0].relevance_score >= result.ranked_articles[-1].relevance_score


@pytest.mark.asyncio
async def test_newsletter_node_renders_html():
    """Newsletter node renders non-empty HTML."""
    from app.agents.newsletter_agent import newsletter_node

    articles = [
        RankedArticle(
            url="https://openai.com/blog/gpt5",
            title="GPT-5 Released with 10x Performance",
            source_name="OpenAI Blog",
            feed_url="https://openai.com/rss",
            relevance_score=95.0,
            rank=1,
            category="Model Release",
            executive_summary="OpenAI has released GPT-5.",
            key_takeaways=["10x faster", "Multi-modal", "Available via API"],
            why_it_matters="Transforms the AI landscape.",
        )
    ]

    state = AgentState(
        run_id="test-wf-newsletter",
        ranked_articles=articles,
        quick_trends=["LLMs getting smarter"],
        market_signals=["$10B investment"],
        research_highlights=["RLHF breakthrough"],
    )

    result = await newsletter_node(state)

    assert result.newsletter_html is not None
    assert len(result.newsletter_html) > 500
    assert "GPT-5" in result.newsletter_html
    assert "AI Daily Brief" in result.newsletter_html
    assert result.newsletter_text is not None
