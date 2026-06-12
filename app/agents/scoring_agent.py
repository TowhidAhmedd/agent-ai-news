"""
Relevance Scoring Agent — uses LLM to score each article 0–100.
Batches articles to reduce API calls.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.article import AgentState, RawArticle, ScoredArticle
from app.utils.config import get_settings
from app.utils.llm_factory import get_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)

BATCH_SIZE = 5          # articles per LLM call
MAX_CONCURRENT = 3      # parallel LLM calls


SCORE_SYSTEM_PROMPT = """You are an AI news curator for a senior AI/ML engineer.
Score each article 0-100 on RELEVANCE to:
- Generative AI, LLMs, Foundation Models
- AI Agents, Multi-agent systems
- RAG, Vector Databases, Embeddings
- OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, Cohere
- LangChain, LangGraph, LlamaIndex
- AI Infrastructure, MLOps, AI Chips
- AI Research breakthroughs
- AI Product launches & funding rounds
- Open-source AI tools & models
- AI startups

Score 0-100:
- 80-100: Must-read, direct relevance, high impact
- 60-79: Highly relevant, important development
- 40-59: Relevant, useful context
- 20-39: Tangentially related
- 0-19: Not relevant

Respond ONLY with valid JSON array. No markdown, no extra text.
Format: [{"index": 0, "score": 85, "category": "Model Release", "reason": "..."}]
"""


async def scoring_node(state: AgentState) -> AgentState:
    """LangGraph node: score articles for AI relevance."""
    t0 = time.monotonic()
    articles = state.extracted_articles
    logger.info("scoring_node: start", total=len(articles))

    # Build batches
    batches = [articles[i:i + BATCH_SIZE] for i in range(0, len(articles), BATCH_SIZE)]

    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def _score_batch_safe(batch, offset):
        async with sem:
            return await _score_batch(batch, offset)

    tasks = [_score_batch_safe(b, i * BATCH_SIZE) for i, b in enumerate(batches)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge results
    score_map: dict[int, dict] = {}
    for r in results:
        if isinstance(r, dict):
            score_map.update(r)

    settings = get_settings()
    scored: list[ScoredArticle] = []
    for idx, art in enumerate(articles):
        info = score_map.get(idx, {})
        score = float(info.get("score", 30))
        if score >= settings.MIN_RELEVANCE_SCORE:
            scored.append(
                ScoredArticle(
                    **art.model_dump(),
                    relevance_score=score,
                    score_breakdown={
                        "category": info.get("category", "General"),
                        "reason": info.get("reason", ""),
                    },
                )
            )

    logger.info(
        "scoring_node: done",
        scored=len(scored),
        discarded=len(articles) - len(scored),
        elapsed=round(time.monotonic() - t0, 2),
    )

    state.scored_articles = scored
    state.total_articles_after_scoring = len(scored)
    state.node_timings["scoring"] = round(time.monotonic() - t0, 2)
    return state


async def _score_batch(batch: list[RawArticle], offset: int) -> dict[int, dict]:
    """Score a batch of articles; return {original_index: score_info}."""
    llm = get_llm()

    items = []
    for i, art in enumerate(batch):
        text_snippet = (art.full_text or art.summary or "")[:400]
        items.append(
            f'{{"index": {offset + i}, "title": {json.dumps(art.title)}, '
            f'"source": {json.dumps(art.source_name)}, '
            f'"snippet": {json.dumps(text_snippet)}}}'
        )

    user_msg = "Score these articles:\n[" + ",\n".join(items) + "]"

    try:
        response = await llm.ainvoke(
            [SystemMessage(content=SCORE_SYSTEM_PROMPT), HumanMessage(content=user_msg)]
        )
        raw = response.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data: list[dict] = json.loads(raw)
        return {item["index"]: item for item in data}
    except Exception as exc:
        logger.warning("Batch scoring failed", error=str(exc))
        # Fallback: give every article in the batch a default score
        return {offset + i: {"score": 50, "category": "General", "reason": "fallback"} for i in range(len(batch))}
