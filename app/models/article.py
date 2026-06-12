"""
Pydantic models for the AI News Agent.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class RawArticle(BaseModel):
    """Article as collected from RSS / scraping."""
    url: str
    title: str
    source_name: str
    feed_url: str
    published_at: Optional[datetime] = None
    author: Optional[str] = None
    summary: Optional[str] = None          # RSS snippet
    full_text: Optional[str] = None        # After extraction


class ScoredArticle(RawArticle):
    """Article with relevance score attached."""
    relevance_score: float = 0.0
    score_breakdown: dict = Field(default_factory=dict)


class SummarizedArticle(ScoredArticle):
    """Article with AI-generated summary."""
    executive_summary: Optional[str] = None
    key_takeaways: list[str] = Field(default_factory=list)
    why_it_matters: Optional[str] = None
    category: Optional[str] = None         # e.g. "Model Release", "Funding"


class RankedArticle(SummarizedArticle):
    """Final ranked article ready for newsletter."""
    rank: int = 0


# ---------------------------------------------------------------------------
# LangGraph workflow state
# ---------------------------------------------------------------------------

class AgentState(BaseModel):
    """Shared state threaded through all LangGraph nodes."""
    run_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)

    # Discovery
    raw_articles: list[RawArticle] = Field(default_factory=list)
    discovery_errors: list[str] = Field(default_factory=list)

    # After extraction
    extracted_articles: list[RawArticle] = Field(default_factory=list)
    extraction_errors: list[str] = Field(default_factory=list)

    # After scoring
    scored_articles: list[ScoredArticle] = Field(default_factory=list)

    # After dedup
    deduplicated_articles: list[ScoredArticle] = Field(default_factory=list)

    # After summarisation
    summarized_articles: list[SummarizedArticle] = Field(default_factory=list)
    summarization_errors: list[str] = Field(default_factory=list)

    # After ranking
    ranked_articles: list[RankedArticle] = Field(default_factory=list)

    # Newsletter
    newsletter_html: Optional[str] = None
    newsletter_text: Optional[str] = None
    quick_trends: list[str] = Field(default_factory=list)
    market_signals: list[str] = Field(default_factory=list)
    research_highlights: list[str] = Field(default_factory=list)

    # Email
    email_sent: bool = False
    email_error: Optional[str] = None

    # Diagnostics
    node_timings: dict[str, float] = Field(default_factory=dict)
    total_articles_discovered: int = 0
    total_articles_after_scoring: int = 0
    total_articles_after_dedup: int = 0


# ---------------------------------------------------------------------------
# DB-facing schemas (plain dataclasses used by SQLAlchemy models)
# ---------------------------------------------------------------------------

class NewsletterRunSchema(BaseModel):
    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str = "running"          # running | success | failed
    articles_discovered: int = 0
    articles_final: int = 0
    email_sent: bool = False
    error_message: Optional[str] = None


class EmailLogSchema(BaseModel):
    run_id: str
    sent_at: datetime
    recipient: str
    subject: str
    success: bool
    error_message: Optional[str] = None
