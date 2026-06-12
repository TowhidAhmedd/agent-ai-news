"""
LangGraph Workflow — wires all agent nodes into a directed state graph.
Every node is wrapped with timing, error-handling, and LangSmith tracing.
"""
from __future__ import annotations

import traceback
import uuid
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable

from langgraph.graph import END, StateGraph

from app.agents import (
    discovery_node,
    dedup_node,
    email_node,
    extraction_node,
    newsletter_node,
    ranking_node,
    scoring_node,
    summarization_node,
)
from app.models.article import AgentState
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Node wrapper — adds error resilience + logging
# ---------------------------------------------------------------------------

def safe_node(name: str, fn: Callable) -> Callable:
    """Wraps a node so errors are logged but don't crash the graph."""

    @wraps(fn)
    async def wrapper(state: AgentState) -> AgentState:
        logger.info(f"▶ {name}")
        try:
            return await fn(state)
        except Exception as exc:
            logger.error(f"✖ {name} failed", error=str(exc), tb=traceback.format_exc())
            # Let the graph continue — downstream nodes handle missing data
            return state

    return wrapper


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def build_workflow() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("discovery", safe_node("discovery", discovery_node))
    graph.add_node("extraction", safe_node("extraction", extraction_node))
    graph.add_node("scoring", safe_node("scoring", scoring_node))
    graph.add_node("dedup", safe_node("dedup", dedup_node))
    graph.add_node("summarization", safe_node("summarization", summarization_node))
    graph.add_node("ranking", safe_node("ranking", ranking_node))
    graph.add_node("newsletter", safe_node("newsletter", newsletter_node))
    graph.add_node("email", safe_node("email", email_node))

    graph.set_entry_point("discovery")
    graph.add_edge("discovery", "extraction")
    graph.add_edge("extraction", "scoring")
    graph.add_edge("scoring", "dedup")
    graph.add_edge("dedup", "summarization")
    graph.add_edge("summarization", "ranking")
    graph.add_edge("ranking", "newsletter")
    graph.add_edge("newsletter", "email")
    graph.add_edge("email", END)

    return graph.compile()


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------

async def run_pipeline(run_id: str | None = None) -> AgentState:
    """Execute the full news agent pipeline and return the final state."""
    run_id = run_id or str(uuid.uuid4())
    logger.info("Pipeline starting", run_id=run_id)

    initial_state = AgentState(
        run_id=run_id,
        started_at=datetime.now(timezone.utc),
    )

    app = build_workflow()

    # Pass config for LangSmith tracing
    config: dict[str, Any] = {
        "configurable": {"run_id": run_id},
        "run_name": f"ai-news-agent-{run_id[:8]}",
    }

    final_state: AgentState = await app.ainvoke(initial_state, config=config)

    logger.info(
        "Pipeline finished",
        run_id=run_id,
        email_sent=final_state.email_sent,
        articles=len(final_state.ranked_articles),
        timings=final_state.node_timings,
    )

    return final_state
