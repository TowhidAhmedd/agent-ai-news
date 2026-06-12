"""
Newsletter Generation Agent — renders the Jinja2 HTML email template.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.article import AgentState
from app.services.rss_feeds import get_all_feeds
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

TEMPLATE_DIR = Path(__file__).parent.parent / "templates"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )


async def newsletter_node(state: AgentState) -> AgentState:
    """LangGraph node: render the newsletter HTML."""
    t0 = time.monotonic()
    settings = get_settings()
    articles = state.ranked_articles
    logger.info("newsletter_node: start", articles=len(articles))

    now_utc = datetime.now(timezone.utc)
    date_str = now_utc.strftime("%A, %B %-d, %Y")
    generated_at = now_utc.strftime("%Y-%m-%d %H:%M UTC")

    env = _get_jinja_env()
    template = env.get_template("newsletter.html")

    html = template.render(
        date=date_str,
        generated_at=generated_at,
        timezone=settings.TIMEZONE,
        articles=articles,
        total_articles=state.total_articles_discovered,
        top_n=len(articles),
        feed_count=len(get_all_feeds()),
        quick_trends=state.quick_trends,
        market_signals=state.market_signals,
        research_highlights=state.research_highlights,
    )

    # Plain-text fallback
    text_lines = [
        f"AI Daily Brief — {date_str}",
        "=" * 60,
        "",
    ]
    for art in articles:
        text_lines.append(f"#{art.rank} {art.title}")
        text_lines.append(f"   Source: {art.source_name}")
        if art.executive_summary:
            text_lines.append(f"   {art.executive_summary}")
        text_lines.append(f"   {art.url}")
        text_lines.append("")

    if state.quick_trends:
        text_lines.append("QUICK TRENDS")
        for t in state.quick_trends:
            text_lines.append(f"  • {t}")
        text_lines.append("")

    logger.info(
        "newsletter_node: done",
        html_len=len(html),
        elapsed=round(time.monotonic() - t0, 2),
    )

    state.newsletter_html = html
    state.newsletter_text = "\n".join(text_lines)
    state.node_timings["newsletter"] = round(time.monotonic() - t0, 2)
    return state
