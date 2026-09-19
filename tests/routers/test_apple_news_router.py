import json
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

import feedparser
import pytest
from bs4 import BeautifulSoup

from router.apple_news import apple_news_router
from router.apple_news.apple_news_router import (
    AppleNewsroomRouter,
    _article_publication_date,
    _parse_feed_date,
)
from utils.feed_item_object import FeedItem, Metadata


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-09-16T14:59:29.399Z", "2026-09-16T14:59:29.399000+00:00"),
        ("2026-09-16T07:59:29-07:00", "2026-09-16T14:59:29+00:00"),
        ("2026-08-03Z", "2026-08-03T00:00:00+00:00"),
        ("2026-08-03", "2026-08-03T00:00:00+00:00"),
        ("Wed, 16 Sep 2026 14:59:29 GMT", "2026-09-16T14:59:29+00:00"),
        (datetime(2026, 9, 16, tzinfo=timezone.utc), "2026-09-16T00:00:00+00:00"),
        (None, None),
        ("", None),
        ("not a date", None),
    ],
)
def test_parse_apple_dates(value, expected):
    result = _parse_feed_date(value)
    assert (result.isoformat() if result else None) == expected


def _router():
    return AppleNewsroomRouter(
        router_path="/apple/newsroom",
        feed_title="Apple Newsroom",
        original_link="https://www.apple.com/newsroom/",
        articles_link="https://www.apple.com/ca/newsroom/rss-feed.rss",
        description="Apple Newsroom",
        language="en-us",
    )


def _page(published="2026-08-03Z"):
    structured = {
        "@graph": [
            {"@type": "Organization", "datePublished": "2000-01-01"},
            {"@type": "NewsArticle", "datePublished": published, "dateModified": "2026-09-08T17:45:10Z"},
        ]
    }
    return BeautifulSoup(
        '<script type="application/ld+json">invalid json</script>'
        '<script type="application/ld+json">' + json.dumps(structured) + "</script>"
        '<article><div class="pagebody"><div class="pagebody-copy">'
        "Full article text</div></div></article>",
        "html.parser",
    )


def test_article_uses_publication_date_not_modification_or_organization_date():
    assert _article_publication_date(_page()) == datetime(2026, 8, 3, tzinfo=timezone.utc)


def test_article_without_publication_date_does_not_use_modification_date():
    assert _article_publication_date(_page(None)) is None


@pytest.mark.parametrize("raw_date", ["September 14, 2026", "not a date"])
def test_article_without_jsonld_uses_only_a_valid_dated_byline(raw_date):
    soup = BeautifulSoup(
        '<span class="category-eyebrow__date">' + raw_date + "</span>",
        "html.parser",
    )
    expected = datetime(2026, 9, 14, tzinfo=timezone.utc) if raw_date.startswith("September") else None
    assert _article_publication_date(soup) == expected


def test_newsroom_discovery_parses_atom_updated_when_published_is_invalid(monkeypatch):
    feed = feedparser.parse("""<feed xmlns="http://www.w3.org/2005/Atom">
      <title>Apple Newsroom</title>
      <entry><title>Article</title><link href="https://www.apple.com/ca/newsroom/story/"/>
        <published>invalid</published><updated>2026-09-16T14:59:29.399Z</updated>
      </entry>
    </feed>""")
    monkeypatch.setattr(apple_news_router, "safe_parse_feed", lambda _url: feed)

    articles = _router()._get_articles_list()

    assert len(articles) == 1
    assert articles[0].created_time == datetime(2026, 9, 16, 14, 59, 29, 399000, timezone.utc)


def _cached_article(monkeypatch):
    key = "router_cache:apple-newsroom:legacy"
    original = {
        "title": "Cached article",
        "link": "https://www.apple.com/ca/newsroom/story/",
        "guid": "stable-guid",
        "description": "<p>Existing full content</p>",
        "author": "Apple",
        "created_time": None,
        "with_content": True,
        "extra": "preserve this field",
    }
    payloads = {key: dict(original)}
    writes = []

    def write(key, payload):
        writes.append(key)
        payloads[key] = payload

    monkeypatch.setattr(apple_news_router, "read_feed_item_from_cache", payloads.get)
    monkeypatch.setattr(apple_news_router, "write_feed_item_to_cache", write)
    monkeypatch.setattr("router.base_router.read_feed_item_from_cache", payloads.get)
    metadata = Metadata(
        title=original["title"], link=original["link"], guid=original["guid"], cache_key=key
    )
    return metadata, payloads, writes, original


def test_legacy_date_repair_preserves_payload_and_renders_rss_pubdate(monkeypatch):
    metadata, payloads, writes, original = _cached_article(monkeypatch)
    monkeypatch.setattr(apple_news_router, "get_link_content_with_bs_no_params", lambda _url: _page())
    router = _router()

    entry = router._get_article(metadata)
    rss = router._generate_response(datetime.now(timezone.utc), [entry], None).rss()

    assert writes == [metadata.cache_key]
    assert payloads[metadata.cache_key] == dict(original, created_time="2026-08-03T00:00:00+00:00")
    assert metadata.created_time == datetime(2026, 8, 3, tzinfo=timezone.utc)
    pubdate = ElementTree.fromstring(rss).findtext("./channel/item/pubDate")
    assert pubdate is not None
    assert parsedate_to_datetime(pubdate) == datetime(2026, 8, 3, tzinfo=timezone.utc)

    def unexpected_fetch(_url):
        pytest.fail("a repaired cache entry must not refetch the article")

    monkeypatch.setattr(apple_news_router, "get_link_content_with_bs_no_params", unexpected_fetch)
    router._get_article(metadata)
    assert writes == [metadata.cache_key]


def test_legacy_date_repair_falls_back_to_atom_time_on_fetch_failure(monkeypatch):
    metadata, payloads, writes, original = _cached_article(monkeypatch)
    metadata.created_time = "2026-09-16T14:59:29.399Z"

    def fail(_url):
        raise TimeoutError("upstream timeout")

    monkeypatch.setattr(apple_news_router, "get_link_content_with_bs_no_params", fail)

    entry = _router()._get_article(metadata)

    assert entry.created_time == datetime(2026, 9, 16, 14, 59, 29, 399000, timezone.utc)
    assert entry.description == original["description"]
    assert writes == [metadata.cache_key]


def test_unrecoverable_date_keeps_existing_payload_without_inventing_date(monkeypatch):
    metadata, payloads, writes, original = _cached_article(monkeypatch)
    monkeypatch.setattr(apple_news_router, "get_link_content_with_bs_no_params", lambda _url: _page(None))

    entry = _router()._get_article(metadata)

    assert entry.created_time is None
    assert writes == []
    assert payloads[metadata.cache_key] == original


def test_read_path_never_repairs_dates_or_fetches_articles(monkeypatch):
    metadata, _payloads, writes, _original = _cached_article(monkeypatch)

    def unexpected_fetch(_url):
        pytest.fail("feed reads must not fetch upstream content")

    monkeypatch.setattr(apple_news_router, "get_link_content_with_bs_no_params", unexpected_fetch)

    entries = _router()._build_feed_entries_from_metadata([metadata])

    assert len(entries) == 1
    assert writes == []


@pytest.mark.parametrize("published", ["2026-08-03Z", None])
def test_new_article_persists_publication_date_or_atom_fallback(monkeypatch, published):
    monkeypatch.setattr(apple_news_router, "get_link_content_with_bs_no_params", lambda _url: _page(published))
    stored = {}
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda key, value: stored.update(value))
    metadata = Metadata(
        title="New article", link="https://www.apple.com/ca/newsroom/new/",
        created_time=datetime(2026, 9, 16, tzinfo=timezone.utc),
    )
    entry = FeedItem(title=metadata.title, link=metadata.link, guid=metadata.link)

    _router()._get_article_content(metadata, entry)

    expected = datetime(2026, 8, 3, tzinfo=timezone.utc) if published else metadata.created_time
    assert entry.created_time == expected
    assert entry.created_time is not None
    assert stored["created_time"] == str(expected)
    assert "Full article text" in stored["description"]
