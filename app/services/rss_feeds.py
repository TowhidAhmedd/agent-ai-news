"""
RSS feed registry.  Add / remove feeds here without touching agent code.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedConfig:
    name: str
    url: str
    category: str = "general"


# ---------------------------------------------------------------------------
# Official AI Lab blogs
# ---------------------------------------------------------------------------
LAB_FEEDS: list[FeedConfig] = [
    FeedConfig("OpenAI Blog", "https://openai.com/blog/rss.xml", "lab"),
    FeedConfig("Anthropic News", "https://www.anthropic.com/news/rss.xml", "lab"),
    FeedConfig("Google DeepMind Blog", "https://deepmind.google/discover/blog/rss.xml", "lab"),
    FeedConfig("Meta AI Blog", "https://ai.meta.com/blog/rss/", "lab"),
    FeedConfig("Hugging Face Blog", "https://huggingface.co/blog/feed.xml", "lab"),
    FeedConfig("Mistral AI Blog", "https://mistral.ai/news/rss.xml", "lab"),
    FeedConfig("Microsoft AI Blog", "https://blogs.microsoft.com/ai/feed/", "lab"),
    FeedConfig("AWS Machine Learning", "https://aws.amazon.com/blogs/machine-learning/feed/", "lab"),
    FeedConfig("LangChain Blog", "https://blog.langchain.dev/rss/", "framework"),
    FeedConfig("Google AI Blog", "https://blog.research.google/feeds/posts/default?alt=rss", "lab"),
]

# ---------------------------------------------------------------------------
# Tech media
# ---------------------------------------------------------------------------
MEDIA_FEEDS: list[FeedConfig] = [
    FeedConfig("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "media"),
    FeedConfig("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "media"),
    FeedConfig("The Decoder", "https://the-decoder.com/feed/", "media"),
    FeedConfig("MIT Technology Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed", "media"),
    FeedConfig("Analytics Vidhya", "https://www.analyticsvidhya.com/feed/", "media"),
    FeedConfig("Towards Data Science", "https://towardsdatascience.com/feed", "community"),
    FeedConfig("The Gradient", "https://thegradient.pub/rss/", "research"),
    FeedConfig("Import AI", "https://jack-clark.net/feed/", "research"),
]

# ---------------------------------------------------------------------------
# All feeds combined
# ---------------------------------------------------------------------------
ALL_FEEDS: list[FeedConfig] = LAB_FEEDS + MEDIA_FEEDS


def get_all_feeds() -> list[FeedConfig]:
    return ALL_FEEDS


def add_feed(name: str, url: str, category: str = "general") -> FeedConfig:
    """Convenience function — append a new feed at runtime."""
    feed = FeedConfig(name=name, url=url, category=category)
    ALL_FEEDS.append(feed)  # type: ignore[attr-defined]  # list is mutable
    return feed
