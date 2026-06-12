"""
Pytest configuration and shared fixtures.
"""
import os
import pytest

# Set test environment variables before any imports
os.environ.setdefault("LLM_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY", "test-key-not-real")
os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_agent.db")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("EMAIL_TO", "test@example.com")
os.environ.setdefault("SMTP_USERNAME", "test@example.com")
os.environ.setdefault("SMTP_PASSWORD", "testpassword")


@pytest.fixture(autouse=True)
def reset_lru_caches():
    """Reset lru_cache'd singletons between tests."""
    from app.utils.config import get_settings
    from app.utils.llm_factory import get_llm
    get_settings.cache_clear()
    get_llm.cache_clear()
    yield
    get_settings.cache_clear()
    get_llm.cache_clear()
