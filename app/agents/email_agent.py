"""
Email Delivery Agent — sends the newsletter via SMTP with retry logic.
Supports Gmail, Outlook, and custom SMTP.
"""
from __future__ import annotations

import asyncio
import smtplib
import ssl
import time
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.models.article import AgentState
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def email_node(state: AgentState) -> AgentState:
    """LangGraph node: send the newsletter email."""
    t0 = time.monotonic()
    settings = get_settings()

    if not state.newsletter_html:
        logger.error("email_node: no newsletter HTML — skipping")
        state.email_error = "No newsletter content generated"
        return state

    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        logger.warning("email_node: SMTP credentials not configured — skipping send")
        state.email_error = "SMTP credentials not configured"
        return state

    subject = _build_subject(state)
    logger.info("email_node: sending", recipient=settings.EMAIL_TO, subject=subject)

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            _send_with_retry,
            subject,
            state.newsletter_html,
            state.newsletter_text or "",
            settings,
        )
        state.email_sent = True
        logger.info("email_node: sent successfully", elapsed=round(time.monotonic() - t0, 2))
    except Exception as exc:
        state.email_error = str(exc)
        logger.error("email_node: failed", error=str(exc))

    state.node_timings["email"] = round(time.monotonic() - t0, 2)
    return state


def _build_subject(state: AgentState) -> str:
    date_str = datetime.now(timezone.utc).strftime("%b %-d")
    n = len(state.ranked_articles)
    top_title = state.ranked_articles[0].title[:50] if state.ranked_articles else "AI News"
    return f"🤖 AI Daily Brief {date_str}: {top_title}... (+{n - 1} more)"


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_exception_type(Exception),
)
def _send_with_retry(subject: str, html: str, text: str, settings) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM or settings.SMTP_USERNAME}>"
    msg["To"] = settings.EMAIL_TO
    msg["X-Mailer"] = "AI-News-Agent/1.0"

    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls(context=context)
        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.sendmail(
            settings.EMAIL_FROM or settings.SMTP_USERNAME,
            settings.EMAIL_TO,
            msg.as_string(),
        )
