import datetime as dt

from router.reuters.reuters_router import ReutersRouter
from utils.feed_item_object import (
    FeedItem,
    Metadata,
    convert_router_path_to_cache_prefix,
    generate_cache_key,
)


def build_router():
    return ReutersRouter(
        router_path="/reuters",
        feed_title="Reuters",
        original_link="https://www.reuters.com/",
        articles_link="https://www.reuters.com/pf/api/v3/content/fetch/",
        description="Reuters",
        language="en-us",
    )


def install_cache_fakes(monkeypatch, metadata_lists=None, feed_items=None, last_build_times=None):
    metadata_lists = metadata_lists or {}
    feed_items = feed_items or {}
    last_build_times = last_build_times or {}

    def replace_metadata(key, value):
        metadata_lists[key] = [dict(item.__dict__) for item in value]

    monkeypatch.setattr("router.reuters.reuters_router.read_metadata_list", lambda key: metadata_lists.get(key))
    monkeypatch.setattr("router.reuters.reuters_router.replace_metadata_list", replace_metadata)
    monkeypatch.setattr("router.reuters.reuters_router.read_last_build_time", lambda key: None)
    monkeypatch.setattr("router.reuters.reuters_router.write_last_build_time", lambda key, value: last_build_times.__setitem__(key, value))
    monkeypatch.setattr("router.reuters.reuters_router.read_feed_item_from_cache", lambda key: feed_items.get(key))
    monkeypatch.setattr("router.reuters.reuters_router.acquire_cache_lock", lambda name: "token")
    monkeypatch.setattr("router.reuters.reuters_router.release_cache_lock", lambda name, token: None)
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda key, payload: feed_items.__setitem__(key, payload))
    return metadata_lists, feed_items, last_build_times


def test_title_cache_key_reuses_existing_same_title_within_three_hours():
    router = build_router()
    existing = [
        {
            "title": "  Same   Story ",
            "created_time": "2026-05-13T10:00:00+00:00",
            "cache_key": "router_cache:reuters:existing",
        }
    ]

    cache_key = router._build_title_cache_key(
        "Same Story",
        "2026-05-13T12:30:00Z",
        "reuters-id",
        existing,
    )

    assert cache_key == "router_cache:reuters:existing"


def test_title_cache_key_uses_different_date_outside_three_hours():
    router = build_router()
    existing = [
        {
            "title": "Same Story",
            "created_time": "2026-05-13T10:00:00+00:00",
            "cache_key": router._build_title_cache_key("Same Story", "2026-05-13T10:00:00Z", "old", []),
        }
    ]

    cache_key = router._build_title_cache_key(
        "Same Story",
        "2026-05-14T10:00:00Z",
        "new",
        existing,
    )

    assert cache_key != existing[0]["cache_key"]


def test_title_cache_key_same_day_outside_three_hours_disambiguates():
    """Same UTC date, but timestamps >3h apart: title|date keys collide, so the
    collision handler must disambiguate using the stable source identifier."""
    router = build_router()
    existing_key = router._build_title_cache_key(
        "Same Story",
        "2026-05-13T01:00:00Z",
        "old",
        [],
    )
    existing = [
        {
            "title": "Same Story",
            "created_time": "2026-05-13T01:00:00+00:00",
            "cache_key": existing_key,
        }
    ]

    cache_key = router._build_title_cache_key(
        "Same Story",
        "2026-05-13T05:00:01Z",
        "new",
        existing,
    )

    expected_disambiguated = generate_cache_key(
        convert_router_path_to_cache_prefix("/reuters"),
        "Same Story|2026-05-13|new",
    )
    assert cache_key != existing_key
    assert cache_key == expected_disambiguated


def test_merge_reuters_metadata_replaces_existing_by_cache_key():
    router = build_router()
    incoming = [Metadata(title="Reuters title", link="https://reuters.com/a", guid="rid", cache_key="shared")]
    existing = [
        {"title": "Yahoo title", "link": "https://yahoo.com/a", "guid": "yid", "cache_key": "shared"},
        {"title": "Old title", "link": "https://reuters.com/old", "guid": "old", "cache_key": "old"},
    ]

    merged = router._merge_reuters_metadata(existing, incoming)

    assert [item.title for item in merged] == ["Reuters title", "Old title"]
    assert merged[0].link == "https://reuters.com/a"


def test_merge_yahoo_metadata_is_additive_only():
    router = build_router()
    incoming = [
        Metadata(title="Yahoo shared", link="https://yahoo.com/shared", guid="ys", cache_key="shared"),
        Metadata(title="Yahoo new", link="https://yahoo.com/new", guid="yn", cache_key="new"),
    ]
    existing = [
        {"title": "Reuters shared", "link": "https://reuters.com/shared", "guid": "rs", "cache_key": "shared"},
        {"title": "Old title", "link": "https://reuters.com/old", "guid": "old", "cache_key": "old"},
    ]

    merged = router._merge_yahoo_metadata(existing, incoming)

    assert [item.cache_key for item in merged] == ["new", "shared", "old"]
    assert merged[1].title == "Reuters shared"


def test_reuters_refresh_persists_payload_under_final_cache_key(monkeypatch):
    router = build_router()
    metadata = Metadata(
        title="Shared Story",
        link="https://www.reuters.com/world/shared/",
        guid="rid",
        created_time="2026-05-13T10:00:00Z",
        cache_key="provisional",
    )
    final_key = router._build_title_cache_key(metadata.title, metadata.created_time, metadata.guid, [])
    metadata_lists, feed_items, last_build_times = install_cache_fakes(monkeypatch)
    reuters_entry = FeedItem(
        title=metadata.title,
        link=metadata.link,
        guid=metadata.guid,
        created_time=metadata.created_time,
        description="<p>Reuters body</p>",
    )

    monkeypatch.setattr(router, "_get_articles_list", lambda **kwargs: [metadata])
    monkeypatch.setattr(router, "_build_reuters_article_entry", lambda article_metadata: reuters_entry)

    refreshed = router.refresh_cache(parameter={"category": "world"}, force=True)

    article_list_key = router._metadata_list_cache_key({"category": "world"})
    assert refreshed is True
    assert metadata_lists[article_list_key][0]["cache_key"] == final_key
    assert reuters_entry.cache_key == final_key
    assert feed_items[final_key]["description"] == "<p>Reuters body</p>"
    assert "/reuters/world" in last_build_times
    assert "/reuters/world/None" not in last_build_times


def test_yahoo_only_article_is_added_to_reuters_cache_and_metadata(monkeypatch):
    router = build_router()
    yahoo_metadata = Metadata(
        title="Yahoo Only Story",
        link="https://www.yahoo.com/news/articles/yahoo-only.html",
        guid="https://www.yahoo.com/news/articles/yahoo-only.html",
        created_time="2026-05-13T10:00:00Z",
        cache_key="provisional-yahoo-key",
    )
    final_key = router._build_title_cache_key(
        yahoo_metadata.title,
        yahoo_metadata.created_time,
        yahoo_metadata.link,
        [],
    )
    metadata_lists, feed_items, _ = install_cache_fakes(monkeypatch)
    yahoo_entry = FeedItem(
        title=yahoo_metadata.title,
        link=yahoo_metadata.link,
        guid=yahoo_metadata.guid,
        created_time=yahoo_metadata.created_time,
        description="<p>Yahoo body</p>",
    )

    monkeypatch.setattr(router, "_fetch_yahoo_page", lambda url: object())
    monkeypatch.setattr(router, "_parse_yahoo_articles", lambda soup, category, existing_metadata: [yahoo_metadata] if category == "world" else [])
    monkeypatch.setattr(router, "_build_yahoo_article_entry", lambda article_metadata: yahoo_entry)

    refreshed = router.refresh_from_yahoo()

    article_list_key = router._metadata_list_cache_key({"category": "world"})
    assert refreshed is True
    assert metadata_lists[article_list_key][0]["cache_key"] == final_key
    assert metadata_lists[article_list_key][0]["link"] == yahoo_metadata.link
    assert yahoo_entry.cache_key == final_key
    assert feed_items[final_key]["description"] == "<p>Yahoo body</p>"


def test_reuters_successful_refresh_overwrites_existing_yahoo_content(monkeypatch):
    router = build_router()
    final_key = router._build_title_cache_key("Shared Story", "2026-05-13T10:00:00Z", "yahoo-url", [])
    parameter = {"category": "world"}
    article_list_key = router._metadata_list_cache_key(parameter)
    metadata_lists = {
        article_list_key: [
            {
                "title": "Shared Story",
                "link": "https://www.yahoo.com/news/articles/shared.html",
                "guid": "https://www.yahoo.com/news/articles/shared.html",
                "created_time": "2026-05-13T10:00:00Z",
                "cache_key": final_key,
            }
        ]
    }
    feed_items = {final_key: {"description": "<p>Yahoo body</p>"}}
    install_cache_fakes(monkeypatch, metadata_lists=metadata_lists, feed_items=feed_items)
    reuters_metadata = Metadata(
        title="Shared Story",
        link="https://www.reuters.com/world/shared/",
        guid="reuters-id",
        created_time="2026-05-13T11:00:00Z",
        cache_key=final_key,
    )

    monkeypatch.setattr(router, "_get_articles_list", lambda **kwargs: [reuters_metadata])
    monkeypatch.setattr(
        router,
        "_build_reuters_article_entry",
        lambda article_metadata: FeedItem(
            title=article_metadata.title,
            link=article_metadata.link,
            guid=article_metadata.guid,
            created_time=article_metadata.created_time,
            description="<p>Reuters body</p>",
        ),
    )

    refreshed = router.refresh_cache(parameter=parameter, force=True)

    assert refreshed is True
    assert feed_items[final_key]["description"] == "<p>Reuters body</p>"
    assert metadata_lists[article_list_key][0]["link"] == "https://www.reuters.com/world/shared/"
    assert metadata_lists[article_list_key][0]["guid"] == "reuters-id"


def test_reuters_content_failure_leaves_existing_yahoo_content_untouched(monkeypatch):
    router = build_router()
    final_key = router._build_title_cache_key("Shared Story", "2026-05-13T10:00:00Z", "yahoo-url", [])
    parameter = {"category": "world"}
    article_list_key = router._metadata_list_cache_key(parameter)
    metadata_lists = {
        article_list_key: [
            {
                "title": "Shared Story",
                "link": "https://www.yahoo.com/news/articles/shared.html",
                "guid": "https://www.yahoo.com/news/articles/shared.html",
                "created_time": "2026-05-13T10:00:00Z",
                "cache_key": final_key,
            }
        ]
    }
    feed_items = {final_key: {"description": "<p>Yahoo body</p>"}}
    install_cache_fakes(monkeypatch, metadata_lists=metadata_lists, feed_items=feed_items)
    reuters_metadata = Metadata(
        title="Shared Story",
        link="https://www.reuters.com/world/shared/",
        guid="reuters-id",
        created_time="2026-05-13T11:00:00Z",
        cache_key=final_key,
    )

    monkeypatch.setattr(router, "_get_articles_list", lambda **kwargs: [reuters_metadata])
    monkeypatch.setattr(router, "_build_reuters_article_entry", lambda article_metadata: None)

    refreshed = router.refresh_cache(parameter=parameter, force=True)

    assert refreshed is True
    assert feed_items[final_key]["description"] == "<p>Yahoo body</p>"
    assert metadata_lists[article_list_key][0]["link"] == "https://www.reuters.com/world/shared/"


def test_reuters_api_blocker_response_does_not_persist_or_fallback(monkeypatch):
    router = build_router()
    metadata = Metadata(
        title="Blocked Story",
        link="https://www.reuters.com/world/blocked/",
        guid="reuters-id",
        created_time="2026-05-13T11:00:00Z",
        cache_key="router_cache:reuters:blocked",
    )
    writes = {}

    monkeypatch.setattr(
        router,
        "_fetch_with_requests",
        lambda url: {
            "status": 401,
            "json": None,
            "error": None,
            "url": url,
            "text": "Please enable JS and disable any ad blocker",
        },
    )
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda key, payload: writes.__setitem__(key, payload))

    entry = FeedItem(title=metadata.title, link=metadata.link, guid=metadata.guid)
    router._get_article_content(metadata, entry)

    assert writes == {}
    assert entry.description is None
    assert router._build_reuters_article_entry(metadata) is None


def test_reuters_invalid_published_time_is_not_replaced_with_epoch():
    router = build_router()
    created_time = router._ReutersRouter__resolve_created_time(
        {
            "id": "reuters-id",
            "title": "Missing Timestamp Story",
            "canonical_url": "/world/missing-timestamp/",
        }
    )

    cache_key = router._build_title_cache_key(
        "Missing Timestamp Story",
        created_time,
        "reuters-id",
        [],
    )

    assert created_time is None
    assert cache_key == generate_cache_key(
        convert_router_path_to_cache_prefix("/reuters"),
        "Missing Timestamp Story",
    )


def test_yahoo_refresh_skips_non_empty_existing_reuters_content(monkeypatch):
    router = build_router()
    final_key = router._build_title_cache_key("Shared Story", "2026-05-13T10:00:00Z", "reuters-id", [])
    parameter = {"category": "world"}
    article_list_key = router._metadata_list_cache_key(parameter)
    metadata_lists = {
        article_list_key: [
            {
                "title": "Shared Story",
                "link": "https://www.reuters.com/world/shared/",
                "guid": "reuters-id",
                "created_time": "2026-05-13T10:00:00Z",
                "cache_key": final_key,
            }
        ]
    }
    feed_items = {final_key: {"description": "<p>Reuters body</p>"}}
    install_cache_fakes(monkeypatch, metadata_lists=metadata_lists, feed_items=feed_items)
    yahoo_metadata = Metadata(
        title="Shared Story",
        link="https://www.yahoo.com/news/articles/shared.html",
        guid="https://www.yahoo.com/news/articles/shared.html",
        created_time="2026-05-13T11:00:00Z",
        cache_key=final_key,
    )

    monkeypatch.setattr(router, "_fetch_yahoo_page", lambda url: object())
    monkeypatch.setattr(router, "_parse_yahoo_articles", lambda soup, category, existing_metadata: [yahoo_metadata] if category == "world" else [])
    monkeypatch.setattr(
        router,
        "_build_yahoo_article_entry",
        lambda article_metadata: FeedItem(
            title=article_metadata.title,
            link=article_metadata.link,
            guid=article_metadata.guid,
            created_time=article_metadata.created_time,
            description="<p>Yahoo body</p>",
        ),
    )

    refreshed = router.refresh_from_yahoo()

    assert refreshed is True
    assert feed_items[final_key]["description"] == "<p>Reuters body</p>"
    assert metadata_lists[article_list_key][0]["link"] == "https://www.reuters.com/world/shared/"


def test_parse_to_utc_datetime_accepts_datetime_and_iso_strings():
    router = build_router()

    assert router._parse_to_utc_datetime("2026-05-13T10:00:00Z") == dt.datetime(2026, 5, 13, 10, tzinfo=dt.timezone.utc)
    assert router._parse_to_utc_datetime(dt.datetime(2026, 5, 13, 10)) == dt.datetime(2026, 5, 13, 10, tzinfo=dt.timezone.utc)
    assert router._parse_to_utc_datetime("not a date") is None
