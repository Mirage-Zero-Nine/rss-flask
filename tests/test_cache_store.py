import datetime as dt
import json

from utils.cache_store import _merge_metadata_dicts, _metadata_to_dict, metadata_list_key, router_last_build_time_key
from utils.feed_item_object import Metadata


def test_metadata_keys_are_namespaced_by_suffix():
    assert metadata_list_key("router_cache:test") == "router_cache:test:metadata-list"
    assert router_last_build_time_key("router_cache:test") == "router_cache:test:last-build-time"


def test_merge_metadata_prefers_incoming_and_appends_existing_items():
    existing = [
        {"cache_key": "old-1", "title": "old one"},
        {"cache_key": "shared", "title": "stale title"},
    ]
    incoming = [
        {"cache_key": "shared", "title": "fresh title"},
        {"cache_key": "new-1", "title": "new one"},
    ]

    assert _merge_metadata_dicts(existing, incoming) == [
        {"cache_key": "shared", "title": "fresh title"},
        {"cache_key": "new-1", "title": "new one"},
        {"cache_key": "old-1", "title": "old one"},
    ]


def test_metadata_to_dict_serializes_datetime():
    created_time = dt.datetime(2026, 5, 13, 10, 30, tzinfo=dt.timezone.utc)
    metadata = Metadata(title="Title", link="https://example.com", guid="guid", created_time=created_time)

    payload = _metadata_to_dict(metadata)

    assert payload["created_time"] == created_time.isoformat()
    json.dumps(payload)
