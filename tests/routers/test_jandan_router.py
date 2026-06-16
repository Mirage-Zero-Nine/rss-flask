from bs4 import BeautifulSoup

from router.jandan.jandan_constant import jandan_description, jandan_page_prefix, jandan_title
from router.jandan.jandan_router import JandanRouter
from utils.feed_item_object import FeedItem, Metadata, convert_router_path_to_cache_prefix, generate_cache_key
from utils.router_constants import html_parser


def build_router():
    return JandanRouter(
        router_path="/jandan",
        feed_title=jandan_title,
        original_link=jandan_page_prefix,
        articles_link=jandan_page_prefix,
        description=jandan_description,
        language="zh-cn",
    )


def test_get_articles_list_normalizes_relative_links_and_keeps_existing_cache_key(monkeypatch):
    listing_html = """
    <div class="post-item row">
        <h2><a href="/p/122943/">A normal Jandan article</a></h2>
    </div>
    <div class="post-item row">
        <h2><a href="/p/122944/">今日好价</a></h2>
    </div>
    """
    soup = BeautifulSoup(listing_html, html_parser)
    monkeypatch.setattr(
        "router.jandan.jandan_router.get_link_content_with_header_and_empty_cookie",
        lambda *args, **kwargs: soup,
    )

    articles = build_router()._get_articles_list()

    assert len(articles) == 1
    article = articles[0]
    assert article.link == "https://jandan.net/p/122943/"
    assert article.guid == "https://jandan.net/p/122943/"

    cache_prefix = convert_router_path_to_cache_prefix("/jandan")
    assert article.cache_key == generate_cache_key(cache_prefix, "/p/122943/")


def test_get_article_content_persists_under_metadata_cache_key(monkeypatch):
    article_html = """
    <a class="post-author">煎蛋作者</a>
    <div class="post-meta">发布于 2026.06.16 @ 12:30</div>
    <div class="post-content"><p>Article body</p></div>
    """
    soup = BeautifulSoup(article_html, html_parser)
    monkeypatch.setattr(
        "router.jandan.jandan_router.get_link_content_with_header_and_empty_cookie",
        lambda *args, **kwargs: soup,
    )
    persisted = {}
    monkeypatch.setattr(
        "utils.feed_item_object.write_feed_item_to_cache",
        lambda key, payload: persisted.setdefault(key, payload),
    )
    metadata = Metadata(
        title="A normal Jandan article",
        link="https://jandan.net/p/122943/",
        guid="https://jandan.net/p/122943/",
        cache_key="router_cache:jandan:legacy-relative-key",
    )
    entry = FeedItem(title=metadata.title, link=metadata.link, guid=metadata.guid)

    build_router()._get_article_content(metadata, entry)

    assert list(persisted) == ["router_cache:jandan:legacy-relative-key"]
    assert persisted["router_cache:jandan:legacy-relative-key"]["link"] == "https://jandan.net/p/122943/"
    assert "<p>Article body</p>" in persisted["router_cache:jandan:legacy-relative-key"]["description"]
