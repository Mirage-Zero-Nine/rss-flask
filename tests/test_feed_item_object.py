import datetime as dt

import pytest

from utils.feed_item_object import (
    FeedItem,
    Metadata,
    convert_router_path_to_cache_prefix,
    generate_cache_key,
)


def test_convert_router_path_to_cache_prefix():
    assert convert_router_path_to_cache_prefix("/zaobao/realtime") == "router_cache:zaobao-realtime"


def test_convert_router_path_to_cache_prefix_rejects_invalid_path():
    with pytest.raises(Exception, match="Invalid path"):
        convert_router_path_to_cache_prefix("zaobao/realtime")


def test_generate_cache_key_uses_urlsafe_base64_and_truncates_long_names():
    cache_key = generate_cache_key("router_cache:test", "https://example.com/" + ("article/" * 50))

    prefix, encoded_name = cache_key.split(":", 1)
    assert prefix == "router_cache"
    assert encoded_name.startswith("test:")
    assert len(encoded_name.removeprefix("test:")) <= 100
    assert "=" not in encoded_name


def test_metadata_dataclass_has_safe_defaults():
    metadata = Metadata()

    assert metadata.title == ""
    assert metadata.link == ""
    assert metadata.guid == ""
    assert metadata.cache_key == ""
    assert metadata.author is None
    assert metadata.created_time is None
    assert metadata.flag is None


def test_feed_item_persist_to_cache_writes_string_payload(monkeypatch):
    captured = {}

    def fake_write(key, payload):
        captured["key"] = key
        captured["payload"] = payload

    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", fake_write)

    created = dt.datetime(2026, 5, 13, 10, 30, tzinfo=dt.timezone.utc)
    entry = FeedItem(
        title="Title",
        link="https://example.com/post",
        description="<p>Body</p>",
        author="Author",
        guid="guid-1",
        created_time=created,
        with_content=True,
    )

    entry.persist_to_cache("/example")

    assert captured["key"] == entry.cache_key
    assert entry.cache_key.startswith("router_cache:example:")

    payload = captured["payload"]
    assert payload["title"] == "Title"
    assert payload["link"] == "https://example.com/post"
    assert payload["description"] == "<p>Body</p>"
    assert payload["author"] == "Author"
    assert payload["guid"] == "guid-1"
    assert payload["created_time"] == str(created)  # stringified for JSON safety
    assert payload["with_content"] is True


def test_feed_item_persist_to_cache_serializes_none_description_as_none(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "utils.feed_item_object.write_feed_item_to_cache",
        lambda key, payload: captured.update({"key": key, "payload": payload}),
    )

    entry = FeedItem(title="t", link="https://example.com/a", guid="g")

    entry.persist_to_cache("/example")

    # None description must remain None so the read path can drop the entry.
    assert captured["payload"]["description"] is None
    # Empty/None created_time serializes as None, not the string "None".
    assert captured["payload"]["created_time"] is None


def test_feed_item_persist_to_cache_prefers_guid_over_link_for_cache_key(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "utils.feed_item_object.write_feed_item_to_cache",
        lambda key, payload: captured.update({"key": key}),
    )

    guid_entry = FeedItem(title="t", link="https://example.com/link", guid="stable-guid")
    link_entry = FeedItem(title="t", link="https://example.com/link", guid=None)
    title_entry = FeedItem(title="title-only", link=None, guid=None)

    guid_entry.persist_to_cache("/example")
    guid_key = captured["key"]
    link_entry.persist_to_cache("/example")
    link_key = captured["key"]
    title_entry.persist_to_cache("/example")
    title_key = captured["key"]

    # guid-derived key differs from link-derived key, link-derived differs from title-derived.
    assert guid_key != link_key
    assert link_key != title_key
    # All keys share the router prefix.
    for key in (guid_key, link_key, title_key):
        assert key.startswith("router_cache:example:")

