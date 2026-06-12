"""
Deduplication Agent — removes duplicate and near-duplicate articles.
Uses URL normalisation + title TF-IDF cosine similarity.
"""
from __future__ import annotations

import re
import time
from urllib.parse import urlparse

from app.models.article import AgentState, ScoredArticle
from app.utils.logger import get_logger

logger = get_logger(__name__)

SIMILARITY_THRESHOLD = 0.75     # cosine similarity cutoff


async def dedup_node(state: AgentState) -> AgentState:
    """LangGraph node: deduplicate scored articles."""
    t0 = time.monotonic()
    articles = state.scored_articles
    logger.info("dedup_node: start", total=len(articles))

    # Step 1 — URL dedup (exact + normalised)
    url_seen: set[str] = set()
    url_deduped: list[ScoredArticle] = []
    for art in articles:
        norm = _normalise_url(art.url)
        if norm not in url_seen:
            url_seen.add(norm)
            url_deduped.append(art)

    # Step 2 — Title near-dup detection via simple word-overlap
    final: list[ScoredArticle] = []
    title_tokens: list[set[str]] = []

    for art in url_deduped:
        tokens = _tokenise(art.title)
        duplicate = False
        for seen_tokens in title_tokens:
            if _jaccard(tokens, seen_tokens) >= SIMILARITY_THRESHOLD:
                duplicate = True
                break
        if not duplicate:
            final.append(art)
            title_tokens.append(tokens)

    logger.info(
        "dedup_node: done",
        before=len(articles),
        after=len(final),
        removed=len(articles) - len(final),
        elapsed=round(time.monotonic() - t0, 2),
    )

    state.deduplicated_articles = final
    state.total_articles_after_dedup = len(final)
    state.node_timings["dedup"] = round(time.monotonic() - t0, 2)
    return state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_url(url: str) -> str:
    """Strip tracking params, fragments, trailing slashes."""
    try:
        p = urlparse(url)
        norm = f"{p.scheme}://{p.netloc}{p.path}".rstrip("/").lower()
        return norm
    except Exception:
        return url.lower()


def _tokenise(text: str) -> set[str]:
    STOP = {"the", "a", "an", "and", "or", "for", "in", "on", "at", "to",
            "of", "with", "is", "are", "was", "how", "why", "what", "new"}
    words = set(re.sub(r"[^a-z0-9\s]", "", text.lower()).split())
    return words - STOP


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union
