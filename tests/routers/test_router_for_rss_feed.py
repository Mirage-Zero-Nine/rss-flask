"""Tests for router.router_for_rss_feed.RouterForRssFeed.

This base class provides _get_articles_list for any router whose source is an
RSS/Atom feed. We mock feedparser.parse to keep tests offline.
"""

from types import SimpleNamespace

from router.router_for_rss_feed import RouterForRssFeed
from utils.feed_item_object import Metadata


def build_router():
    return RouterForRssFeed(
        router_path="/example/feed",
        feed_title="Example Feed",
        original_link="https://example.com",
        articles_link="https://example.com/feed.xml",
        description="Example",
        language="en-us",
    )


def _make_feed(entries):
    """Build a feedparser-like result object using SimpleNamespace.

    feedparser entries expose attributes like .title, .link, .published. We mimic
    just enough of that surface for RouterForRssFeed._get_articles_list to work.
    """
    parsed_entries = [
        SimpleNamespace(title=title, link=link, published=published)
        for title, link, published in entries
    ]
    return SimpleNamespace(entries=parsed_entries, bozo=False, bozo_exception=None, get=lambda key, default=None: default)


def test_get_articles_list_builds_metadata_for_each_entry(monkeypatch):
    feed = _make_feed([
        ("Story one", "https://example.com/one", "Mon, 13 May 2026 10:00:00 GMT"),
        ("Story two", "https://example.com/two", "Mon, 13 May 2026 11:00:00 GMT"),
    ])
    monkeypatch.setattr("router.router_for_rss_feed.feedparser.parse", lambda url: feed)

    metadata_list = build_router()._get_articles_list()

    assert len(metadata_list) == 2
    assert all(isinstance(item, Metadata) for item in metadata_list)
    assert [m.title for m in metadata_list] == ["Story one", "Story two"]
    assert [m.link for m in metadata_list] == ["https://example.com/one", "https://example.com/two"]
    for metadata in metadata_list:
        assert metadata.cache_key.startswith("router_cache:example-feed:")


def test_get_articles_list_filters_entries_by_link_prefix(monkeypatch):
    feed = _make_feed([
        ("Drop me", "https://www.meta.com/blog/promo", "Mon, 13 May 2026 10:00:00 GMT"),
        ("Keep me", "https://engineering.example.com/post", "Mon, 13 May 2026 11:00:00 GMT"),
    ])
    monkeypatch.setattr("router.router_for_rss_feed.feedparser.parse", lambda url: feed)

    metadata_list = build_router()._get_articles_list(link_filter="https://www.meta")

    titles = [m.title for m in metadata_list]
    assert titles == ["Keep me"]


def test_get_articles_list_filters_entries_by_title_prefix(monkeypatch):
    feed = _make_feed([
        ("雇员招聘启事 - drop", "https://example.com/hiring", "Mon, 13 May 2026 10:00:00 GMT"),
        ("Real headline", "https://example.com/news", "Mon, 13 May 2026 11:00:00 GMT"),
    ])
    monkeypatch.setattr("router.router_for_rss_feed.feedparser.parse", lambda url: feed)

    metadata_list = build_router()._get_articles_list(title_filter="雇员招聘启事")

    assert [m.title for m in metadata_list] == ["Real headline"]


def test_get_articles_list_skips_entries_missing_link_or_title(monkeypatch):
    feed = _make_feed([
        ("Has both", "https://example.com/a", "Mon, 13 May 2026 10:00:00 GMT"),
        ("", "https://example.com/no-title", "Mon, 13 May 2026 10:00:00 GMT"),
        ("No link", "", "Mon, 13 May 2026 10:00:00 GMT"),
    ])
    monkeypatch.setattr("router.router_for_rss_feed.feedparser.parse", lambda url: feed)

    metadata_list = build_router()._get_articles_list()

    assert [m.title for m in metadata_list] == ["Has both"]


def test_get_articles_list_returns_empty_when_feed_has_no_entries(monkeypatch):
    feed = _make_feed([])
    monkeypatch.setattr("router.router_for_rss_feed.feedparser.parse", lambda url: feed)

    assert build_router()._get_articles_list() == []
