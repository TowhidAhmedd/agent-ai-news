"""
News Discovery Agent — fetches articles from all configured RSS feeds.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional

import feedparser
import httpx

from app.models.article import AgentState, RawArticle
from app.services.rss_feeds import get_all_feeds
from app.utils.logger import get_logger

logger = get_logger(__name__)

FETCH_TIMEOUT = 20          # seconds per feed
MAX_ARTICLES_PER_FEED = 15


async def discovery_node(state: AgentState) -> AgentState:
    """LangGraph node: discover articles from all RSS feeds."""
    t0 = time.monotonic()
    logger.info("discovery_node: start")

    feeds = get_all_feeds()
    all_articles: list[RawArticle] = []
    errors: list[str] = []

    async with httpx.AsyncClient(
        timeout=FETCH_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": "AI-News-Agent/1.0 (+https://github.com/ai-news-agent)"},
    ) as client:
        tasks = [_fetch_feed(client, feed) for feed in feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for feed_cfg, result in zip(feeds, results):
        if isinstance(result, Exception):
            msg = f"{feed_cfg.name}: {result}"
            logger.warning("Feed fetch error", feed=feed_cfg.name, error=str(result))
            errors.append(msg)
        else:
            articles, errs = result
            all_articles.extend(articles)
            errors.extend(errs)

    logger.info(
        "discovery_node: done",
        discovered=len(all_articles),
        errors=len(errors),
        elapsed=round(time.monotonic() - t0, 2),
    )

    state.raw_articles = all_articles
    state.discovery_errors = errors
    state.total_articles_discovered = len(all_articles)
    state.node_timings["discovery"] = round(time.monotonic() - t0, 2)
    return state


async def _fetch_feed(
    client: httpx.AsyncClient,
    feed_cfg,
) -> tuple[list[RawArticle], list[str]]:
    articles: list[RawArticle] = []
    errors: list[str] = []

    try:
        resp = await client.get(feed_cfg.url)
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
    except Exception as exc:
        return [], [f"{feed_cfg.name}: {exc}"]

    for entry in parsed.entries[:MAX_ARTICLES_PER_FEED]:
        try:
            art = _entry_to_article(entry, feed_cfg)
            if art:
                articles.append(art)
        except Exception as exc:
            errors.append(f"{feed_cfg.name} entry error: {exc}")

    return articles, errors


def _entry_to_article(entry, feed_cfg) -> Optional[RawArticle]:
    url = entry.get("link") or entry.get("id")
    title = entry.get("title", "").strip()
    if not url or not title:
        return None

    # Published date
    pub_at: Optional[datetime] = None
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        t = entry.get(field)
        if t:
            try:
                pub_at = datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
            break

    # Summary / snippet
    summary = ""
    if hasattr(entry, "summary"):
        from bs4 import BeautifulSoup
        summary = BeautifulSoup(entry.summary, "html.parser").get_text(separator=" ").strip()
        summary = summary[:500]

    author = entry.get("author") or entry.get("dc_creator")

    return RawArticle(
        url=url,
        title=title,
        source_name=feed_cfg.name,
        feed_url=feed_cfg.url,
        published_at=pub_at,
        author=author,
        summary=summary,
    )
