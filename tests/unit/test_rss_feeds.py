"""Unit tests for RSS feed registry."""
import pytest
from app.services.rss_feeds import get_all_feeds, FeedConfig, add_feed


class TestFeedRegistry:
    def test_feeds_not_empty(self):
        feeds = get_all_feeds()
        assert len(feeds) > 0

    def test_all_feeds_have_url(self):
        for feed in get_all_feeds():
            assert feed.url.startswith("http")

    def test_all_feeds_have_name(self):
        for feed in get_all_feeds():
            assert len(feed.name) > 0

    def test_add_feed(self):
        before = len(get_all_feeds())
        new_feed = add_feed("Test Feed", "https://example.com/rss", "test")
        after = len(get_all_feeds())
        assert after == before + 1
        assert new_feed.name == "Test Feed"

    def test_feed_config_frozen(self):
        feed = FeedConfig("Test", "https://example.com/rss", "general")
        with pytest.raises((AttributeError, TypeError)):
            feed.name = "Changed"
