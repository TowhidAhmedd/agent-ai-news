"""
Centralised settings loaded from environment / .env file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ------------------------------------------------------------------ App
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "sqlite:///./data/news_agent.db"
    MAX_ARTICLES_PER_RUN: int = 100
    TOP_N_ARTICLES: int = 10
    MIN_RELEVANCE_SCORE: float = 40.0
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ------------------------------------------------------------------ LLM
    LLM_PROVIDER: Literal["openrouter", "groq", "gemini"] = "groq"

    # OpenRouter
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"

    # Groq
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Gemini
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # ------------------------------------------------------------------ LangSmith
    LANGCHAIN_TRACING_V2: bool = False
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "ai-news-agent"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # ------------------------------------------------------------------ Email
    EMAIL_TO: str = "towhid4635@gmail.com"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: Optional[str] = None
    EMAIL_FROM_NAME: str = "AI News Agent"

    # ------------------------------------------------------------------ Schedule
    SCHEDULE_HOUR: int = 6
    SCHEDULE_MINUTE: int = 30
    TIMEZONE: str = "Asia/Dhaka"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
