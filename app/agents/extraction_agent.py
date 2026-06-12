"""
Content Extraction Agent — fetches full article text from URLs.
Uses newspaper3k with BeautifulSoup fallback.
"""
from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from app.models.article import AgentState, RawArticle
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

MAX_WORKERS = 8
FULL_TEXT_MAX_CHARS = 6000       # truncate to keep token cost low


async def extraction_node(state: AgentState) -> AgentState:
    """LangGraph node: extract full text for each raw article."""
    t0 = time.monotonic()
    settings = get_settings()
    articles = state.raw_articles[: settings.MAX_ARTICLES_PER_RUN]

    logger.info("extraction_node: start", total=len(articles))

    loop = asyncio.get_event_loop()
    extracted: list[RawArticle] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            loop.run_in_executor(pool, _extract_article, art): art
            for art in articles
        }
        results = await asyncio.gather(*futures.keys(), return_exceptions=True)

    for art, result in zip(articles, results):
        if isinstance(result, Exception):
            # Keep article with whatever text we already have
            art_copy = art.model_copy()
            if not art_copy.full_text:
                art_copy.full_text = art_copy.summary or ""
            extracted.append(art_copy)
            errors.append(f"{art.url}: {result}")
        else:
            extracted.append(result)

    logger.info(
        "extraction_node: done",
        extracted=len(extracted),
        errors=len(errors),
        elapsed=round(time.monotonic() - t0, 2),
    )

    state.extracted_articles = extracted
    state.extraction_errors = errors
    state.node_timings["extraction"] = round(time.monotonic() - t0, 2)
    return state


def _extract_article(article: RawArticle) -> RawArticle:
    """Synchronous extraction — runs in thread pool."""
    text = _try_newspaper(article.url)
    if not text or len(text) < 100:
        text = _try_bs4(article.url)

    art = article.model_copy()
    art.full_text = (text or article.summary or "")[:FULL_TEXT_MAX_CHARS]
    return art


def _try_newspaper(url: str) -> str:
    try:
        from newspaper import Article  # type: ignore

        a = Article(url, request_timeout=15)
        a.download()
        a.parse()
        return a.text or ""
    except Exception:
        return ""


def _try_bs4(url: str) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-News-Agent/1.0)"},
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove boilerplate
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "form", "noscript", "iframe"]):
            tag.decompose()

        # Prefer <article> or <main>
        content = soup.find("article") or soup.find("main") or soup.find("body")
        if not content:
            return ""

        paragraphs = content.find_all("p")
        text = " ".join(p.get_text(separator=" ").strip() for p in paragraphs)
        return text.strip()
    except Exception:
        return ""
