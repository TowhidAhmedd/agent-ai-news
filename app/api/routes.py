"""
FastAPI route definitions.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Response

from app.graph.workflow import run_pipeline
from app.repositories.database import get_engine
from app.repositories.run_repo import RunRepository
from app.scheduler.job import _run_job
from app.services.rss_feeds import get_all_feeds
from app.utils.config import get_settings
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", tags=["system"])
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": settings.LLM_PROVIDER,
        "schedule": f"{settings.SCHEDULE_HOUR:02d}:{settings.SCHEDULE_MINUTE:02d} {settings.TIMEZONE}",
        "feeds": len(get_all_feeds()),
    }


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@router.get("/metrics", tags=["system"])
async def metrics() -> dict:
    runs = RunRepository.get_runs(limit=50)
    total = len(runs)
    success = sum(1 for r in runs if r["status"] == "success")
    emails_sent = sum(1 for r in runs if r["email_sent"])
    latest = runs[0] if runs else None
    return {
        "total_runs": total,
        "successful_runs": success,
        "failed_runs": total - success,
        "emails_sent": emails_sent,
        "latest_run": latest,
    }


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

@router.get("/news/latest", tags=["news"])
async def latest_news(limit: int = 20) -> list[dict]:
    return RunRepository.get_latest_articles(limit=limit)


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.get("/runs", tags=["runs"])
async def list_runs(limit: int = 20) -> list[dict]:
    return RunRepository.get_runs(limit=limit)


# ---------------------------------------------------------------------------
# Manual trigger
# ---------------------------------------------------------------------------

@router.post("/run-now", tags=["runs"])
async def run_now(background_tasks: BackgroundTasks) -> dict:
    """Trigger the news pipeline immediately (non-blocking)."""
    background_tasks.add_task(_run_job)
    return {
        "status": "triggered",
        "message": "Pipeline started in background. Check /runs for progress.",
    }


# ---------------------------------------------------------------------------
# Newsletter
# ---------------------------------------------------------------------------

@router.get("/newsletter/latest", tags=["newsletter"])
async def latest_newsletter() -> Response:
    html = RunRepository.get_latest_newsletter()
    if not html:
        raise HTTPException(status_code=404, detail="No newsletter available yet. Run the pipeline first.")
    return Response(content=html, media_type="text/html")
