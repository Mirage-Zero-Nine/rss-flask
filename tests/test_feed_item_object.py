import pytest

from utils.feed_item_object import FeedItem, convert_router_path_to_cache_prefix, generate_cache_key


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


def test_persist_to_cache_uses_override_key(monkeypatch):
    writes = {}
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda key, payload: writes.setdefault(key, payload))

    entry = FeedItem(title="Title", link="https://example.com", guid="guid", description="<p>Body</p>")
    entry.persist_to_cache("/reuters", cache_key_override="router_cache:reuters:shared")

    assert entry.cache_key == "router_cache:reuters:shared"
    assert writes["router_cache:reuters:shared"]["description"] == "<p>Body</p>"
