"""
Ranking Agent — picks the Top-N articles and generates aggregate trends.
"""
from __future__ import annotations

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.article import AgentState, RankedArticle, SummarizedArticle
from app.utils.config import get_settings
from app.utils.llm_factory import get_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)

CATEGORY_WEIGHTS = {
    "Model Release": 1.3,
    "Research": 1.2,
    "Product Launch": 1.1,
    "Funding": 1.0,
    "Open Source": 1.1,
    "Infrastructure": 1.0,
    "Policy": 0.9,
    "General": 0.8,
    "Other": 0.8,
}

TRENDS_SYSTEM_PROMPT = """You are an AI industry analyst. 
Given the list of today's top AI news headlines and summaries, identify:
1. Quick Trends: 3-5 recurring themes across multiple stories (one sentence each)
2. Market Signals: 2-3 important launches, funding rounds, acquisitions, partnerships
3. Research Highlights: 1-2 important papers or technical breakthroughs

Respond ONLY with valid JSON, no markdown:
{
  "quick_trends": ["trend 1", "trend 2"],
  "market_signals": ["signal 1", "signal 2"],
  "research_highlights": ["highlight 1"]
}
"""


async def ranking_node(state: AgentState) -> AgentState:
    """LangGraph node: rank articles and select top N."""
    t0 = time.monotonic()
    settings = get_settings()
    articles = state.summarized_articles
    logger.info("ranking_node: start", total=len(articles))

    # --- Composite score ---
    def composite(art: SummarizedArticle) -> float:
        weight = CATEGORY_WEIGHTS.get(art.category or "Other", 0.9)
        return art.relevance_score * weight

    sorted_articles = sorted(articles, key=composite, reverse=True)
    top_articles = sorted_articles[: settings.TOP_N_ARTICLES]

    ranked = [
        RankedArticle(**art.model_dump(), rank=i + 1)
        for i, art in enumerate(top_articles)
    ]

    # --- Generate aggregate trends via LLM ---
    trends, signals, highlights = await _generate_trends(ranked)

    logger.info(
        "ranking_node: done",
        ranked=len(ranked),
        elapsed=round(time.monotonic() - t0, 2),
    )

    state.ranked_articles = ranked
    state.quick_trends = trends
    state.market_signals = signals
    state.research_highlights = highlights
    state.node_timings["ranking"] = round(time.monotonic() - t0, 2)
    return state


async def _generate_trends(articles: list[RankedArticle]) -> tuple[list, list, list]:
    if not articles:
        return [], [], []

    llm = get_llm()
    headlines = "\n".join(
        f"- [{art.category}] {art.title} ({art.source_name}): {art.executive_summary or ''}"
        for art in articles
    )

    try:
        response = await llm.ainvoke(
            [SystemMessage(content=TRENDS_SYSTEM_PROMPT), HumanMessage(content=headlines)]
        )
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
        return (
            data.get("quick_trends", []),
            data.get("market_signals", []),
            data.get("research_highlights", []),
        )
    except Exception as exc:
        logger.warning("Trend generation failed", error=str(exc))
        return [], [], []
