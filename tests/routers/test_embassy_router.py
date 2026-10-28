"""Embassy HTTPS migration keeps historical RSS GUIDs and Redis identities."""

from copy import deepcopy
from xml.etree import ElementTree

import pytest
from bs4 import BeautifulSoup

from router.embassy.china_embassy_news import ChinaEmbassyNewsRouter
from router.embassy.china_embassy_news_constants import china_embassy_news_prefix
from utils.cache_store import _merge_metadata_dicts
from utils.feed_item_object import Metadata, generate_cache_key


_PATH = "/tzgg/202609/t20260918_12024955.htm"
_LEGACY_URL = "http://losangeles.china-consulate.org" + _PATH
_HTTPS_URL = "https://losangeles.china-consulate.gov.cn" + _PATH
_CACHE_KEY = generate_cache_key("router_cache:embassy", _LEGACY_URL)


def build_router():
    return ChinaEmbassyNewsRouter(
        router_path="/embassy", feed_title="Embassy", original_link=china_embassy_news_prefix,
        articles_link=china_embassy_news_prefix, description="Embassy news", language="zh-cn",
    )


def _listing(monkeypatch, href):
    soup = BeautifulSoup(f'<ul class="tt"><li><a href="{href}">Announcement</a></li></ul>', "html.parser")
    fetched = []

    def fetch(url):
        fetched.append(url)
        return soup

    monkeypatch.setattr("router.embassy.china_embassy_news.get_link_content_with_urllib_request", fetch)
    metadata = build_router()._get_articles_list()
    assert fetched == [china_embassy_news_prefix]
    return metadata


@pytest.mark.parametrize("href", [
    "./202609/t20260918_12024955.htm", "202609/t20260918_12024955.htm", _PATH,
    _HTTPS_URL, _LEGACY_URL, "//losangeles.china-consulate.gov.cn" + _PATH,
])
def test_https_discovery_preserves_historical_guid_and_cache_key(monkeypatch, href):
    metadata = _listing(monkeypatch, href)
    assert len(metadata) == 1
    assert metadata[0].link == _HTTPS_URL
    assert metadata[0].guid == _LEGACY_URL
    assert metadata[0].cache_key == _CACHE_KEY


def test_long_relative_urls_are_resolved_without_length_heuristic(monkeypatch):
    relative = "./202610/an-article-name-that-is-longer-than-thirty-five-characters.htm"
    metadata = _listing(monkeypatch, relative)[0]
    assert metadata.link == (
        "https://losangeles.china-consulate.gov.cn/tzgg/202610/"
        "an-article-name-that-is-longer-than-thirty-five-characters.htm"
    )
    assert metadata.guid == "http://losangeles.china-consulate.org/tzgg" + relative[1:]
    assert metadata.cache_key == generate_cache_key("router_cache:embassy", metadata.guid)


def test_external_https_article_retains_its_own_identity(monkeypatch):
    external = "https://us.china-embassy.gov.cn/notice/article.htm"
    metadata = _listing(monkeypatch, external)[0]
    assert metadata.link == external
    assert metadata.guid == external
    assert metadata.cache_key == generate_cache_key("router_cache:embassy", external)


@pytest.mark.parametrize("href", [
    "javascript:attack()", "https://losangeles.china-consulate.gov.cn:444/notice",
    "https://user:secret@losangeles.china-consulate.gov.cn/notice", "https://[broken/",
])
def test_invalid_urls_are_not_discovered(monkeypatch, href):
    assert _listing(monkeypatch, href) == []


def test_hiring_filter_and_missing_anchor_are_preserved(monkeypatch):
    soup = BeautifulSoup('<ul class="tt"><li>Missing link</li><li><a>No href</a></li>'
                         '<li><a href="./hiring.htm">雇员招聘启事</a></li>'
                         f'<li><a href="{_PATH}">Announcement</a></li></ul>', 'html.parser')
    monkeypatch.setattr("router.embassy.china_embassy_news.get_link_content_with_urllib_request", lambda url: soup)
    metadata = build_router()._get_articles_list(link_filter="雇员招聘启事")
    assert [item.title for item in metadata] == ["Announcement"]


def test_existing_cached_article_reused_without_fetch_or_write_and_renders_same_guid(monkeypatch):
    metadata = _listing(monkeypatch, "./202609/t20260918_12024955.htm")[0]
    old_metadata = vars(metadata).copy()
    old_metadata["link"] = _LEGACY_URL
    payload = {"title": "Announcement", "link": _LEGACY_URL, "guid": _LEGACY_URL,
               "description": "<p>Existing body</p>", "author": "Consulate",
               "created_time": "2026-09-18T10:00:00+00:00", "with_content": True}
    original = deepcopy(payload)
    reads = []

    def read(key):
        reads.append(key)
        return payload if key == _CACHE_KEY else None

    def forbidden(*args, **kwargs):
        pytest.fail("Existing cached article must not be fetched or rewritten")

    monkeypatch.setattr("router.base_router.read_feed_item_from_cache", read)
    monkeypatch.setattr("router.embassy.china_embassy_news.get_link_content_with_urllib_request", forbidden)
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", forbidden)
    router = build_router()
    cached = router._get_article(metadata)
    assert cached.guid == _LEGACY_URL
    assert cached.cache_key == _CACHE_KEY

    # Metadata merge replaces the matching logical item rather than appending
    # the HTTPS spelling as a second item. Rendering updates navigation only.
    merged = _merge_metadata_dicts([old_metadata], [vars(metadata).copy()])
    assert len(merged) == 1
    entries = router._build_feed_entries_from_metadata([Metadata(**item) for item in merged])
    feed = router._generate_response(None, entries, None)
    rss = ElementTree.fromstring(feed.rss())
    assert len(rss.findall("channel/item")) == 1
    assert rss.findtext("channel/item/link") == _HTTPS_URL
    assert rss.findtext("channel/item/guid") == _LEGACY_URL
    assert rss.findtext("channel/item/description") == "<p>Existing body</p>"
    assert reads == [_CACHE_KEY, _CACHE_KEY]
    assert payload == original


@pytest.mark.parametrize("metadata_link", [_HTTPS_URL, _LEGACY_URL])
def test_cache_miss_fetches_https_and_persists_under_the_legacy_key(monkeypatch, metadata_link):
    metadata = Metadata(title="Announcement", link=metadata_link, guid=_LEGACY_URL, cache_key=_CACHE_KEY)
    fetched = []
    writes = []

    def fetch(url):
        fetched.append(url)
        return BeautifulSoup('<div id="News_Body_Time">2026-09-18 10:00</div>'
                             '<div id="News_Body_Txt_A"><p>Announcement body</p></div>', "html.parser")

    monkeypatch.setattr("router.base_router.read_feed_item_from_cache", lambda key: None)
    monkeypatch.setattr("router.embassy.china_embassy_news.get_link_content_with_urllib_request", fetch)
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda key, payload: writes.append((key, payload)))
    entry = build_router()._get_article(metadata)
    assert fetched == [_HTTPS_URL]
    assert entry.link == _HTTPS_URL
    assert entry.guid == _LEGACY_URL
    assert entry.cache_key == _CACHE_KEY
    assert len(writes) == 1
    assert writes[0][0] == _CACHE_KEY
    assert writes[0][1]["link"] == _HTTPS_URL
    assert writes[0][1]["guid"] == _LEGACY_URL
    assert "Announcement body" in writes[0][1]["description"]


def test_content_fetch_failure_does_not_replace_cached_payload(monkeypatch):
    metadata = Metadata(title="Announcement", link=_HTTPS_URL, guid=_LEGACY_URL, cache_key=_CACHE_KEY)
    monkeypatch.setattr("router.base_router.read_feed_item_from_cache", lambda key: None)
    monkeypatch.setattr("router.embassy.china_embassy_news.get_link_content_with_urllib_request", lambda url: None)

    def forbidden(*args, **kwargs):
        pytest.fail("Failed HTTPS fetch must not publish an empty payload")

    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", forbidden)
    assert build_router()._get_article(metadata).description is None
