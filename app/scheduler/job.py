"""
APScheduler job — triggers the news pipeline daily at configured time.
Prevents duplicate concurrent runs.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from app.graph.workflow import run_pipeline
from app.repositories.database import get_engine
from app.repositories.run_repo import RunRepository
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_running = False          # simple concurrency guard


async def _run_job() -> None:
    global _running
    if _running:
        logger.warning("Pipeline already running — skipping duplicate trigger")
        return

    _running = True
    settings = get_settings()
    try:
        logger.info("Scheduled pipeline starting")
        state = await run_pipeline()
        RunRepository.complete_run(state)

        if state.email_sent:
            RunRepository.log_email(
                run_id=state.run_id,
                recipient=settings.EMAIL_TO,
                subject=f"AI Daily Brief – {datetime.utcnow().strftime('%Y-%m-%d')}",
                success=True,
            )
        elif state.email_error:
            RunRepository.log_email(
                run_id=state.run_id,
                recipient=settings.EMAIL_TO,
                subject="AI Daily Brief (failed)",
                success=False,
                error=state.email_error,
            )
    except Exception as exc:
        logger.error("Scheduled job failed", error=str(exc))
    finally:
        _running = False


def create_scheduler() -> AsyncIOScheduler:
    settings = get_settings()

    jobstores = {
        "default": SQLAlchemyJobStore(engine=get_engine()),
    }
    executors = {
        "default": ThreadPoolExecutor(max_workers=1),
    }

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        executors=executors,
        timezone=settings.TIMEZONE,
        job_defaults={"coalesce": True, "max_instances": 1},
    )

    scheduler.add_job(
        _run_job,
        trigger="cron",
        hour=settings.SCHEDULE_HOUR,
        minute=settings.SCHEDULE_MINUTE,
        id="daily_news_briefing",
        replace_existing=True,
        name="Daily AI News Briefing",
    )

    logger.info(
        "Scheduler configured",
        time=f"{settings.SCHEDULE_HOUR:02d}:{settings.SCHEDULE_MINUTE:02d}",
        timezone=settings.TIMEZONE,
    )

    return scheduler
