import datetime as dt

from router.openai_news.openai_news_router import OpenAINewsRouter
from utils.feed_item_object import FeedItem, Metadata


def build_router():
    return OpenAINewsRouter(
        router_path="/openai-news",
        feed_title="OpenAI News",
        original_link="https://openai.com/news/",
        articles_link="https://openai.com/news/rss.xml",
        description="OpenAI news",
        language="en-us",
    )


def test_get_articles_list_filters_by_category(monkeypatch):
    class Feed:
        entries = [
            {
                "title": "Company item",
                "link": "https://openai.com/index/company-item",
                "id": "company-id",
                "published": "Thu, 14 May 2026 13:00:00 GMT",
                "summary": "Company summary",
                "tags": [{"term": "Company"}],
            },
            {
                "title": "Research item",
                "link": "https://openai.com/index/research-item",
                "id": "research-id",
                "published": "Tue, 12 May 2026 00:00:00 GMT",
                "summary": "Research summary",
                "tags": [{"term": "Research"}],
            },
        ]

        def get(self, key, default=None):
            return default

    monkeypatch.setattr("router.openai_news.openai_news_router.feedparser.parse", lambda url: Feed())

    articles = build_router()._get_articles_list(parameter={"category": "research"})

    assert len(articles) == 1
    assert articles[0].title == "Research item"
    assert articles[0].author == "OpenAI"
    assert articles[0].created_time == dt.datetime(2026, 5, 12, tzinfo=dt.timezone.utc)
    assert articles[0].cache_key.startswith("router_cache:openai-news:")


def test_get_articles_list_all_keeps_all_categories(monkeypatch):
    class Feed:
        entries = [
            {"title": "A", "link": "https://openai.com/a", "tags": [{"term": "Company"}]},
            {"title": "B", "link": "https://openai.com/b", "tags": [{"term": "Product"}]},
        ]

        def get(self, key, default=None):
            return default

    monkeypatch.setattr("router.openai_news.openai_news_router.feedparser.parse", lambda url: Feed())

    articles = build_router()._get_articles_list(parameter={"category": "all"})

    assert [article.title for article in articles] == ["A", "B"]


def test_get_article_content_uses_rss_summary(monkeypatch):
    monkeypatch.setattr("router.openai_news.openai_news_router.requests.get", lambda *args, **kwargs: (_ for _ in ()).throw(Exception("blocked")))
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda *args, **kwargs: None)

    entry = FeedItem()
    metadata = Metadata(
        title="Product item",
        link="https://openai.com/product",
        author="OpenAI",
        created_time=dt.datetime(2026, 5, 14, 13, tzinfo=dt.timezone.utc),
        flag={
            "summary": "Use Codex anywhere with the ChatGPT mobile app.",
            "categories": ["Product"],
        },
    )

    build_router()._get_article_content(metadata, entry)

    assert "Use Codex anywhere" in entry.description
    assert "Product" in entry.description
    assert entry.author == "OpenAI"


def test_get_article_content_extracts_article_page_body(monkeypatch):
    html = """
    <html>
      <body>
        <main>
          <p>Table of contents</p>
          <div class="relative w-full">
            <p class="text-meta">May 14, 2026</p>
            <a href="/news/product-releases/">Product</a>
            <h1>Work with Codex from anywhere</h1>
            <p>Codex is coming to your phone. Now in preview in the ChatGPT mobile app.</p>
            <iframe src="https://player.vimeo.com/video/1192355275" title="Lotus_CodexMobile_16x9 from OpenAI on Vimeo"></iframe>
            <img alt="16x9 Art Card" src="//images.ctfassets.net/kftzwdyauwt9/16_9.png" />
          </div>
          <p>Share</p>
          <p>Codex is now in the ChatGPT mobile app so you can stay in the loop from anywhere while Codex gets work done.</p>
          <p>Read more about <a href="/index/running-codex-safely/">running Codex safely</a>.</p>
          <h2>Stay connected to active work from anywhere</h2>
          <p>Codex in the ChatGPT mobile app is a fully-featured mobile experience for getting work done with Codex.</p>
          <ul>
            <li><strong>Start investigating a bug</strong> while waiting for your coffee.</li>
            <li>Reach a decision point during your commute.</li>
          </ul>
          <h2>Author</h2>
          <p>OpenAI</p>
          <h2>Keep reading</h2>
        </main>
      </body>
    </html>
    """

    class Response:
        status_code = 200
        text = html

    monkeypatch.setattr("router.openai_news.openai_news_router.requests.get", lambda *args, **kwargs: Response())
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda *args, **kwargs: None)

    entry = FeedItem()
    metadata = Metadata(
        title="Work with Codex from anywhere",
        link="https://openai.com/index/work-with-codex-from-anywhere/",
        author="OpenAI",
        created_time=dt.datetime(2026, 5, 14, 13, tzinfo=dt.timezone.utc),
        flag={
            "summary": "Short RSS summary",
            "categories": ["Product"],
        },
    )

    build_router()._get_article_content(metadata, entry)

    assert '<iframe' in entry.description
    assert 'src="https://player.vimeo.com/video/1192355275"' in entry.description
    assert "Lotus_CodexMobile_16x9" in entry.description
    assert '<img' in entry.description
    assert 'src="https://images.ctfassets.net/kftzwdyauwt9/16_9.png"' in entry.description
    assert "Codex is now in the ChatGPT mobile app" in entry.description
    assert '<a href="https://openai.com/index/running-codex-safely/">running Codex safely</a>' in entry.description
    assert "Stay connected to active work from anywhere" in entry.description
    compact_description = "".join(entry.description.split())
    assert "<ul><li><strong>Startinvestigatingabug</strong>whilewaitingforyourcoffee.</li><li>Reachadecisionpointduringyourcommute.</li></ul>" in compact_description
    assert "Short RSS summary" not in entry.description
    assert "Keep reading" not in entry.description


def _make_feed_with_one_per_category():
    """Build a fake feedparser result with one entry per OpenAI category term."""

    class Feed:
        entries = [
            {
                "title": "Company A",
                "link": "https://openai.com/index/a",
                "id": "a",
                "tags": [{"term": "Company"}],
            },
            {
                "title": "Research B",
                "link": "https://openai.com/index/b",
                "id": "b",
                "tags": [{"term": "Research"}],
            },
            {
                "title": "Product C",
                "link": "https://openai.com/index/c",
                "id": "c",
                "tags": [{"term": "Product"}],
            },
            {
                "title": "Safety D",
                "link": "https://openai.com/index/d",
                "id": "d",
                "tags": [{"term": "Safety"}],
            },
            {
                "title": "Engineering E",
                "link": "https://openai.com/index/e",
                "id": "e",
                "tags": [{"term": "Engineering"}],
            },
            {
                "title": "Security F",
                "link": "https://openai.com/index/f",
                "id": "f",
                "tags": [{"term": "Security"}],
            },
            {
                "title": "Global Affairs G",
                "link": "https://openai.com/index/g",
                "id": "g",
                "tags": [{"term": "Global Affairs"}],
            },
            {
                "title": "AI Adoption H",
                "link": "https://openai.com/index/h",
                "id": "h",
                "tags": [{"term": "AI Adoption"}],
            },
        ]

        def get(self, key, default=None):
            return default

    return Feed()


def test_refresh_all_categories_parses_rss_feed_once(monkeypatch):
    router = build_router()
    parse_calls = {"count": 0, "categories": []}

    def fake_parse(url):
        parse_calls["count"] += 1
        return _make_feed_with_one_per_category()

    monkeypatch.setattr("router.openai_news.openai_news_router.feedparser.parse", fake_parse)

    # Stub refresh_cache to record category dispatch and avoid touching cache_store.
    def fake_refresh_cache(parameter=None, **_kwargs):
        parse_calls["categories"].append(parameter["category"])
        # Trigger _get_articles_list to confirm it consumes the cached feed.
        articles = router._get_articles_list(parameter=parameter)
        parse_calls.setdefault("article_counts", {})[parameter["category"]] = len(articles)
        return True

    monkeypatch.setattr(router, "refresh_cache", fake_refresh_cache)

    router.refresh_all_categories()

    assert parse_calls["count"] == 1, "RSS feed should be parsed exactly once per bulk refresh"
    assert parse_calls["categories"] == list(router.VALID_CATEGORIES.keys())
    # All 8 entries pass through 'all', plus one per matching category.
    assert parse_calls["article_counts"]["all"] == 8
    assert parse_calls["article_counts"]["company"] == 1
    assert parse_calls["article_counts"]["research"] == 1
    # Cache should be cleared after the bulk operation completes.
    assert router._cached_feed is None


def test_warm_all_categories_parses_rss_feed_once(monkeypatch):
    router = build_router()
    parse_calls = {"count": 0}

    def fake_parse(url):
        parse_calls["count"] += 1
        return _make_feed_with_one_per_category()

    monkeypatch.setattr("router.openai_news.openai_news_router.feedparser.parse", fake_parse)
    monkeypatch.setattr(router, "warm_cache", lambda **_kwargs: False)

    router.warm_all_categories()

    assert parse_calls["count"] == 1
    assert router._cached_feed is None


def test_direct_get_articles_list_call_still_parses_fresh(monkeypatch):
    """A direct (non-bulk) call must not reuse a stale cached feed."""

    router = build_router()
    parse_calls = {"count": 0}

    def fake_parse(url):
        parse_calls["count"] += 1
        return _make_feed_with_one_per_category()

    monkeypatch.setattr("router.openai_news.openai_news_router.feedparser.parse", fake_parse)

    # Two direct calls should both fetch fresh.
    router._get_articles_list(parameter={"category": "all"})
    router._get_articles_list(parameter={"category": "company"})

    assert parse_calls["count"] == 2


def test_with_shared_feed_clears_cache_on_exception(monkeypatch):
    router = build_router()
    monkeypatch.setattr(
        "router.openai_news.openai_news_router.feedparser.parse",
        lambda url: _make_feed_with_one_per_category(),
    )

    def raising_action(_category):
        raise RuntimeError("boom")

    try:
        router._with_shared_feed(raising_action)
    except RuntimeError:
        pass

    assert router._cached_feed is None
