"""
Summarization Agent — generates executive summary, key takeaways, and
"why it matters" for each article using the LLM.
"""
from __future__ import annotations

import asyncio
import json
import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.models.article import AgentState, ScoredArticle, SummarizedArticle
from app.utils.llm_factory import get_llm
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_CONCURRENT = 4


SUMMARIZE_SYSTEM_PROMPT = """You are an expert AI technology journalist writing for senior AI engineers and researchers.
Summarize the article concisely and technically accurately.

Respond ONLY with valid JSON. No markdown fences, no extra text.
Format:
{
  "executive_summary": "2-3 sentence summary",
  "key_takeaways": ["takeaway 1", "takeaway 2", "takeaway 3"],
  "why_it_matters": "1-2 sentence business/research impact explanation",
  "category": "one of: Model Release | Research | Product Launch | Funding | Open Source | Infrastructure | Policy | Other"
}
"""


async def summarization_node(state: AgentState) -> AgentState:
    """LangGraph node: summarize each deduplicated article."""
    t0 = time.monotonic()
    articles = state.deduplicated_articles
    logger.info("summarization_node: start", total=len(articles))

    sem = asyncio.Semaphore(MAX_CONCURRENT)

    async def _summarize_safe(art: ScoredArticle) -> SummarizedArticle:
        async with sem:
            return await _summarize_article(art)

    tasks = [_summarize_safe(art) for art in articles]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    summarized: list[SummarizedArticle] = []
    errors: list[str] = []

    for art, result in zip(articles, results):
        if isinstance(result, Exception):
            errors.append(f"{art.url}: {result}")
            # Fallback: use RSS snippet as summary
            summarized.append(
                SummarizedArticle(
                    **art.model_dump(),
                    executive_summary=art.summary or art.title,
                    key_takeaways=[],
                    why_it_matters="",
                    category="General",
                )
            )
        else:
            summarized.append(result)

    logger.info(
        "summarization_node: done",
        summarized=len(summarized),
        errors=len(errors),
        elapsed=round(time.monotonic() - t0, 2),
    )

    state.summarized_articles = summarized
    state.summarization_errors = errors
    state.node_timings["summarization"] = round(time.monotonic() - t0, 2)
    return state


async def _summarize_article(art: ScoredArticle) -> SummarizedArticle:
    llm = get_llm()
    text = (art.full_text or art.summary or art.title)[:3000]

    prompt = (
        f"Title: {art.title}\n"
        f"Source: {art.source_name}\n"
        f"Article text:\n{text}"
    )

    try:
        response = await llm.ainvoke(
            [SystemMessage(content=SUMMARIZE_SYSTEM_PROMPT), HumanMessage(content=prompt)]
        )
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data: dict = json.loads(raw)
    except Exception as exc:
        logger.warning("Summarization failed", url=art.url, error=str(exc))
        data = {
            "executive_summary": art.summary or art.title,
            "key_takeaways": [],
            "why_it_matters": "",
            "category": "General",
        }

    return SummarizedArticle(
        **art.model_dump(),
        executive_summary=data.get("executive_summary", ""),
        key_takeaways=data.get("key_takeaways", []),
        why_it_matters=data.get("why_it_matters", ""),
        category=data.get("category", "General"),
    )
