"""
Integration tests for the FastAPI endpoints.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    # Set required env vars before importing app
    import os
    os.environ.setdefault("LLM_PROVIDER", "groq")
    os.environ.setdefault("GROQ_API_KEY", "test-key")
    os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_news_agent.db")

    from app.repositories.database import init_db
    init_db()

    from app.main import app
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "timestamp" in data
        assert "feeds" in data


class TestMetricsEndpoint:
    def test_metrics_returns_dict(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_runs" in data
        assert "successful_runs" in data


class TestRunsEndpoint:
    def test_runs_returns_list(self, client):
        resp = client.get("/runs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestNewsEndpoint:
    def test_news_returns_list(self, client):
        resp = client.get("/news/latest")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestNewsletterEndpoint:
    def test_newsletter_404_when_no_data(self, client):
        resp = client.get("/newsletter/latest")
        # Either 200 (has data) or 404 (first run, no data yet)
        assert resp.status_code in (200, 404)
