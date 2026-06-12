"""
Factory that returns the configured LLM client.
Supports OpenRouter, Groq, and Gemini free tiers.
"""
from __future__ import annotations

import os
from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def get_llm() -> BaseChatModel:
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        return _build_groq(settings)
    elif provider == "openrouter":
        return _build_openrouter(settings)
    elif provider == "gemini":
        return _build_gemini(settings)
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")


def _build_groq(settings) -> BaseChatModel:
    try:
        from langchain_groq import ChatGroq  # type: ignore
    except ImportError:
        from langchain_openai import ChatOpenAI
        logger.warning("langchain_groq not installed, falling back via OpenAI-compat")
        return ChatOpenAI(
            openai_api_key=settings.GROQ_API_KEY,
            openai_api_base="https://api.groq.com/openai/v1",
            model=settings.GROQ_MODEL,
            temperature=0.1,
        )

    logger.info("Using Groq LLM", model=settings.GROQ_MODEL)
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_MODEL,
        temperature=0.1,
        max_tokens=2048,
    )


def _build_openrouter(settings) -> BaseChatModel:
    from langchain_openai import ChatOpenAI

    logger.info("Using OpenRouter LLM", model=settings.OPENROUTER_MODEL)
    return ChatOpenAI(
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        model=settings.OPENROUTER_MODEL,
        temperature=0.1,
        max_tokens=2048,
    )


def _build_gemini(settings) -> BaseChatModel:
    from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore

    logger.info("Using Gemini LLM", model=settings.GEMINI_MODEL)
    os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY or ""
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        temperature=0.1,
        max_output_tokens=2048,
    )
