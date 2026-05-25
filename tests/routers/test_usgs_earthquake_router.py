"""Tests for router.earthquake.usgs_earthquake_router.

The USGS router is a Type-3 (JSON API) router that pre-builds article descriptions
into Metadata.flag during _get_articles_list, so _get_article_content makes no
network call. These tests mock requests.get to keep everything offline.
"""

import datetime as dt

from router.earthquake.usgs_earthquake_router import UsgsEarthquakeRouter
from utils.feed_item_object import FeedItem, Metadata


USGS_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"


def build_router():
    return UsgsEarthquakeRouter(
        router_path="/earthquake",
        feed_title="USGS",
        original_link="https://earthquake.usgs.gov/earthquakes/map",
        articles_link=USGS_FEED_URL,
        description="USGS Magnitude 2.5+ Earthquakes, Past Day",
        language="en-us",
    )


def _make_feature(
    *,
    title="M 4.2 - 10km NE of Springfield",
    url="https://earthquake.usgs.gov/earthquakes/eventpage/abc123",
    place="10km NE of Springfield",
    time_ms=1778833800000,  # 2026-05-13 10:30:00 UTC
    depth_km=12.4,
    ce_id="abc123",
):
    return {
        "type": "Feature",
        "properties": {
            "title": title,
            "url": url,
            "place": place,
            "time": time_ms,
            "ids": {"ce": ce_id} if ce_id is not None else None,
        },
        "geometry": {"coordinates": [-122.0, 37.0, depth_km] if depth_km is not None else [-122.0, 37.0]},
    }


def test_build_entry_from_feature_returns_payload_with_html_description():
    feature = _make_feature()

    payload = build_router()._build_entry_from_feature(feature)

    assert payload is not None
    assert payload["title"] == "M 4.2 - 10km NE of Springfield"
    assert payload["link"] == "https://earthquake.usgs.gov/earthquakes/eventpage/abc123"
    assert payload["author"] == "USGS"
    assert payload["guid"] == "abc123"
    assert isinstance(payload["created_time"], dt.datetime)
    desc = payload["description"]
    assert "<p>Location: 10km NE of Springfield</p>" in desc
    assert "<p>Time:" in desc
    assert "<p>Depth: 12.4 KM</p>" in desc
    assert '<a href="https://earthquake.usgs.gov/earthquakes/eventpage/abc123">' in desc


def test_build_entry_from_feature_skips_when_title_is_missing():
    feature = _make_feature(title="")

    assert build_router()._build_entry_from_feature(feature) is None


def test_build_entry_from_feature_skips_when_url_is_missing():
    feature = _make_feature(url="")

    assert build_router()._build_entry_from_feature(feature) is None


def test_build_entry_from_feature_falls_back_when_place_is_missing():
    feature = _make_feature(place=None)

    payload = build_router()._build_entry_from_feature(feature)

    assert payload is not None
    assert "<p>Location: Unknown location</p>" in payload["description"]


def test_get_articles_list_builds_metadata_with_pre_built_description(monkeypatch):
    feature = _make_feature()
    fake_response_json = {"features": [feature]}

    class FakeResponse:
        status_code = 200
        content = b"{}"
        text = ""

        def json(self):
            return fake_response_json

    monkeypatch.setattr(
        "router.earthquake.usgs_earthquake_router.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    metadata_list = build_router()._get_articles_list()

    assert len(metadata_list) == 1
    metadata = metadata_list[0]
    assert isinstance(metadata, Metadata)
    assert metadata.title == "M 4.2 - 10km NE of Springfield"
    assert metadata.cache_key.startswith("router_cache:earthquake:")
    # Pre-built description is stashed in flag so _get_article_content makes no network call.
    assert metadata.flag is not None
    assert "<p>Location:" in metadata.flag
    assert "<p>Depth: 12.4 KM</p>" in metadata.flag


def test_get_articles_list_returns_empty_on_non_200(monkeypatch):
    class FakeResponse:
        status_code = 503
        content = b""
        text = "service unavailable"

        def json(self):  # pragma: no cover - never reached on non-200
            raise AssertionError("json() must not be called on non-200 response")

    monkeypatch.setattr(
        "router.earthquake.usgs_earthquake_router.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )

    assert build_router()._get_articles_list() == []


def test_get_article_content_uses_metadata_flag_and_does_not_call_requests(monkeypatch):
    persisted = {"called": False}

    def record_persist(*args, **kwargs):
        persisted["called"] = True

    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", record_persist)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("USGS _get_article_content must not make HTTP calls")

    monkeypatch.setattr("router.earthquake.usgs_earthquake_router.requests.get", fail_if_called)

    metadata = Metadata(
        title="M 4.2",
        link="https://earthquake.usgs.gov/earthquakes/eventpage/abc123",
        author="USGS",
        guid="abc123",
        cache_key="router_cache:earthquake:abc",
        flag="<p>pre-built body</p>",
    )
    entry = FeedItem()

    result = build_router()._get_article_content(metadata, entry)

    assert entry.description == "<p>pre-built body</p>"
    assert entry.title == "M 4.2"
    assert entry.author == "USGS"
    assert entry.guid == "abc123"
    assert persisted["called"] is True
    assert result == "<p>pre-built body</p>"
