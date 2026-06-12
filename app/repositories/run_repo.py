"""
Repository for newsletter runs and article persistence.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.article import AgentState
from app.repositories.database import (
    ArticleRecord,
    EmailLogRecord,
    NewsletterRunRecord,
    get_session_factory,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _session() -> Session:
    return get_session_factory()()


class RunRepository:

    @staticmethod
    def create_run(run_id: str, started_at: datetime) -> None:
        db = _session()
        try:
            record = NewsletterRunRecord(
                run_id=run_id,
                started_at=started_at,
                status="running",
            )
            db.add(record)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def complete_run(state: AgentState) -> None:
        db = _session()
        try:
            record = db.query(NewsletterRunRecord).filter_by(run_id=state.run_id).first()
            if not record:
                record = NewsletterRunRecord(
                    run_id=state.run_id,
                    started_at=state.started_at,
                )
                db.add(record)

            record.finished_at = datetime.now(timezone.utc)
            record.status = "success" if not state.email_error else "failed"
            record.articles_discovered = state.total_articles_discovered
            record.articles_final = len(state.ranked_articles)
            record.email_sent = state.email_sent
            record.error_message = state.email_error
            record.newsletter_html = state.newsletter_html

            # Persist top articles
            for art in state.ranked_articles:
                article_record = ArticleRecord(
                    run_id=state.run_id,
                    url=art.url,
                    title=art.title,
                    source_name=art.source_name,
                    published_at=art.published_at,
                    author=art.author,
                    relevance_score=art.relevance_score,
                    category=art.category,
                    executive_summary=art.executive_summary,
                    why_it_matters=art.why_it_matters,
                    rank=art.rank,
                )
                db.add(article_record)

            db.commit()
            logger.info("Run persisted", run_id=state.run_id)
        except Exception as exc:
            db.rollback()
            logger.error("Failed to persist run", error=str(exc))
        finally:
            db.close()

    @staticmethod
    def log_email(run_id: str, recipient: str, subject: str, success: bool, error: Optional[str] = None) -> None:
        db = _session()
        try:
            log = EmailLogRecord(
                run_id=run_id,
                recipient=recipient,
                subject=subject,
                success=success,
                error_message=error,
            )
            db.add(log)
            db.commit()
        finally:
            db.close()

    @staticmethod
    def get_runs(limit: int = 20) -> list[dict]:
        db = _session()
        try:
            rows = (
                db.query(NewsletterRunRecord)
                .order_by(NewsletterRunRecord.started_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "run_id": r.run_id,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                    "status": r.status,
                    "articles_discovered": r.articles_discovered,
                    "articles_final": r.articles_final,
                    "email_sent": r.email_sent,
                    "error_message": r.error_message,
                }
                for r in rows
            ]
        finally:
            db.close()

    @staticmethod
    def get_latest_newsletter() -> Optional[str]:
        db = _session()
        try:
            row = (
                db.query(NewsletterRunRecord)
                .filter(NewsletterRunRecord.newsletter_html.isnot(None))
                .order_by(NewsletterRunRecord.started_at.desc())
                .first()
            )
            return row.newsletter_html if row else None
        finally:
            db.close()

    @staticmethod
    def get_latest_articles(limit: int = 20) -> list[dict]:
        db = _session()
        try:
            rows = (
                db.query(ArticleRecord)
                .order_by(ArticleRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "title": r.title,
                    "url": r.url,
                    "source_name": r.source_name,
                    "relevance_score": r.relevance_score,
                    "category": r.category,
                    "executive_summary": r.executive_summary,
                    "rank": r.rank,
                    "published_at": r.published_at.isoformat() if r.published_at else None,
                }
                for r in rows
            ]
        finally:
            db.close()
