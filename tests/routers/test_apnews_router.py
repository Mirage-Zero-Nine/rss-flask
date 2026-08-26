from bs4 import BeautifulSoup

from router.apnews import apnews_router
from router.apnews.apnews_router import ApnewsRouter
from utils.router_constants import html_parser, language_english


def _build_router() -> ApnewsRouter:
    return ApnewsRouter(
        router_path="/apnews/business",
        feed_title="AP News - Business",
        original_link="https://apnews.com/business",
        articles_link="https://apnews.com/business",
        description="AP Business News",
        language=language_english,
        default_topic="business",
    )


def test_apnews_discovery_uses_urllib_with_explicit_headers(monkeypatch):
    captured = {}
    page = BeautifulSoup(
        """
        <div class="PagePromo-content">
          <a href="https://apnews.com/article/example-story">Example story</a>
          <span class="PagePromoContentIcons-text">Example story</span>
        </div>
        """,
        html_parser,
    )

    def fake_fetch(link, headers=None, parser=None):
        captured["link"] = link
        captured["headers"] = headers
        captured["parser"] = parser
        return page

    monkeypatch.setattr(apnews_router, "get_link_content_with_urllib_request", fake_fetch)

    metadata = _build_router()._get_articles_list()

    assert captured["link"] == "https://apnews.com/business"
    assert captured["headers"]["User-Agent"].startswith("rss-flask/")
    assert captured["parser"] == html_parser
    assert len(metadata) == 1
    assert metadata[0].title == "Example story"
