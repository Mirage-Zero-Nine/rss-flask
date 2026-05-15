import datetime as dt

from router.base_router import BaseRouter
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix


class FakeRouter(BaseRouter):
    def __init__(self):
        super().__init__(
            router_path="/fake",
            feed_title="Fake Feed",
            original_link="https://example.com",
            articles_link="https://example.com/feed",
            description="Fake description",
            language="en-us",
            period=600000,
        )
        self.article_list_calls = 0
        self.article_content_calls = 0

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        self.article_list_calls += 1
        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        return [
            Metadata(
                title="Article one",
                link="https://example.com/one",
                guid="https://example.com/one",
                cache_key=generate_cache_key(cache_prefix, "https://example.com/one"),
            )
        ]

    def _get_article_content(self, article_metadata, entry):
        self.article_content_calls += 1
        entry.description = "<p>Body</p>"
        entry.author = "Author"
        entry.created_time = dt.datetime(2026, 5, 13, tzinfo=dt.timezone.utc)
        entry.persist_to_cache(self.router_path)


def install_memory_cache(monkeypatch):
    feed_items = {}
    metadata_lists = {}
    last_build_times = {}

    def write_feed_item(key, payload):
        feed_items[key] = payload

    def read_feed_item(key):
        return feed_items.get(key)

    def write_metadata(cache_key, metadata_list):
        metadata_lists[cache_key] = [dict(metadata.__dict__) for metadata in metadata_list]

    def read_metadata(cache_key):
        return metadata_lists.get(cache_key)

    def write_last_build_time(cache_key, last_build_time):
        last_build_times[cache_key] = last_build_time

    def read_last_build_time(cache_key):
        return last_build_times.get(cache_key)

    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", write_feed_item)
    monkeypatch.setattr("router.base_router.read_feed_item_from_cache", read_feed_item)
    monkeypatch.setattr("router.base_router.write_metadata_list", write_metadata)
    monkeypatch.setattr("router.base_router.read_metadata_list", read_metadata)
    monkeypatch.setattr("router.base_router.write_last_build_time", write_last_build_time)
    monkeypatch.setattr("router.base_router.read_last_build_time", read_last_build_time)
    return feed_items, metadata_lists, last_build_times


def test_get_article_uses_cached_entry_without_refetching(monkeypatch):
    router = FakeRouter()
    cache_key = "router_cache:fake:cached"
    monkeypatch.setattr(
        "router.base_router.read_feed_item_from_cache",
        lambda key: {
            "title": "Cached",
            "link": "https://example.com/cached",
            "description": "<p>Cached body</p>",
            "author": "Cache",
            "guid": "https://example.com/cached",
            "created_time": "2026-05-13T10:30:00+00:00",
            "with_content": True,
        } if key == cache_key else None,
    )

    entry = router._get_article(Metadata(title="Cached", link="https://example.com/cached", guid="guid", cache_key=cache_key))

    assert entry.description == "<p>Cached body</p>"
    assert entry.created_time == dt.datetime(2026, 5, 13, 10, 30, tzinfo=dt.timezone.utc)
    assert router.article_content_calls == 0


def test_get_article_refetches_cached_entry_with_empty_description(monkeypatch):
    router = FakeRouter()
    cache_key = "router_cache:fake:empty"
    feed_items = {}

    monkeypatch.setattr(
        "router.base_router.read_feed_item_from_cache",
        lambda key: {
            "title": "Cached empty",
            "link": "https://example.com/empty",
            "description": "",
            "author": "Cache",
            "guid": "https://example.com/empty",
            "created_time": "2026-05-13T10:30:00+00:00",
            "with_content": True,
        } if key == cache_key else None,
    )
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda key, payload: feed_items.setdefault(key, payload))

    entry = router._get_article(Metadata(title="Cached empty", link="https://example.com/empty", guid="guid", cache_key=cache_key))

    assert entry.description == "<p>Body</p>"
    assert router.article_content_calls == 1
    assert len(feed_items) == 1


def test_refresh_cache_fetches_articles_persists_metadata_and_last_build_time(monkeypatch):
    router = FakeRouter()
    feed_items, metadata_lists, last_build_times = install_memory_cache(monkeypatch)

    refreshed = router.refresh_cache(force=True)

    article_list_key = router._build_article_list_cache_key("/fake")
    assert refreshed is True
    assert router.article_list_calls == 1
    assert router.article_content_calls == 1
    assert len(feed_items) == 1
    assert metadata_lists[article_list_key][0]["title"] == "Article one"
    assert "/fake" in last_build_times


def test_refresh_cache_skips_when_cache_is_fresh(monkeypatch):
    router = FakeRouter()
    _, metadata_lists, last_build_times = install_memory_cache(monkeypatch)
    article_list_key = router._build_article_list_cache_key("/fake")
    metadata_lists[article_list_key] = [{"title": "Existing", "link": "https://example.com/existing", "guid": "guid", "cache_key": "cache"}]
    last_build_times["/fake"] = dt.datetime.now()

    refreshed = router.refresh_cache()

    assert refreshed is False
    assert router.article_list_calls == 0


def test_build_feed_entries_from_metadata_drops_missing_and_none_descriptions(monkeypatch):
    router = FakeRouter()
    payloads = {
        "ok": {"title": "OK", "link": "https://example.com/ok", "description": "<p>OK</p>", "guid": "ok"},
        "none": {"title": "None", "link": "https://example.com/none", "description": None, "guid": "none"},
    }
    monkeypatch.setattr("router.base_router.read_feed_item_from_cache", lambda key: payloads.get(key))
    metadata = [
        Metadata(title="OK", link="https://example.com/ok", guid="ok", cache_key="ok"),
        Metadata(title="None", link="https://example.com/none", guid="none", cache_key="none"),
        Metadata(title="Missing", link="https://example.com/missing", guid="missing", cache_key="missing"),
    ]

    entries = router._build_feed_entries_from_metadata(metadata)

    assert [entry.title for entry in entries] == ["OK"]


def test_build_feed_entries_from_metadata_keeps_empty_description(monkeypatch):
    router = FakeRouter()
    payloads = {
        "ok": {"title": "OK", "link": "https://example.com/ok", "description": "<p>OK</p>", "guid": "ok"},
        "empty": {"title": "Empty", "link": "https://example.com/empty", "description": "", "guid": "empty"},
    }
    monkeypatch.setattr("router.base_router.read_feed_item_from_cache", lambda key: payloads.get(key))
    metadata = [
        Metadata(title="OK", link="https://example.com/ok", guid="ok", cache_key="ok"),
        Metadata(title="Empty", link="https://example.com/empty", guid="empty", cache_key="empty"),
    ]

    entries = router._build_feed_entries_from_metadata(metadata)

    assert [entry.title for entry in entries] == ["OK", "Empty"]
