import json

from bs4 import BeautifulSoup

from router.yahoo_news.yahoo_news_router import YahooNewsRouter
from utils.feed_item_object import FeedItem, Metadata


def build_router():
    return YahooNewsRouter(
        router_path="/yahoo/reuters",
        feed_title="Yahoo Reuters",
        original_link="https://profiles.yahoo.com/brands/reuters/",
        articles_link="https://profiles.yahoo.com/brands/reuters/",
        description="Reuters on Yahoo",
        language="en-us",
    )


def test_parse_articles_for_topic_filters_deduplicates_and_reads_json_ld_dates():
    article_url = "https://www.yahoo.com/news/world-story-1.html"
    html = f"""
    <html>
      <head>
        <script type="application/ld+json">
          {json.dumps({"hasPart": [{"url": article_url, "datePublished": "2026-05-13T10:30:00Z"}]})}
        </script>
      </head>
      <body>
        <div id="strm">
          <a href="{article_url}" data-ylk="elm:hdln;subsec:publisher-brand;cnt_tpc:world">World story</a>
          <a href="https://www.yahoo.com/news/duplicate.html" data-ylk="elm:hdln;subsec:publisher-brand;cnt_tpc:world">World story</a>
          <a href="https://www.yahoo.com/news/business.html" data-ylk="elm:hdln;subsec:publisher-brand;cnt_tpc:business">Business story</a>
          <a href="https://www.yahoo.com/news/ignored.html" data-ylk="elm:hdln;cnt_tpc:world">Ignored story</a>
        </div>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")

    metadata = build_router()._parse_articles_for_topic(soup, "world")

    assert len(metadata) == 1
    assert metadata[0].title == "World story"
    assert metadata[0].link == article_url
    assert metadata[0].author == "Reuters"
    assert metadata[0].created_time == "2026-05-13T10:30:00Z"
    assert metadata[0].cache_key.startswith("router_cache:yahoo-reuters:")


def test_get_article_content_uses_video_json_ld_description(monkeypatch):
    article_url = "https://www.yahoo.com/news/videos/brazil-unveils-fuel-subsidies-congress-040736028.html"
    html = f"""
    <html>
      <head><title>Video story</title></head>
      <body>
        <article>
          <script type="application/ld+json">
            {json.dumps({
                "@type": "NewsArticle",
                "datePublished": "2026-05-14T04:07:36Z",
                "description": "<body><p>Short teaser paragraph that should lose to the full video transcript.</p></body>",
                "image": {"url": "https://example.com/thumbnail.jpg"},
            })}
          </script>
          <script type="application/ld+json">
            {json.dumps({
                "@type": "VideoObject",
                "description": (
                    "<body><p>STORY: Brazil said Wednesday it would provide a direct subsidy "
                    "for producers and importers of gasoline, and later diesel.</p>"
                    "<p>That's after a proposal stalled in Congress and officials needed "
                    "another way to reduce pump prices.</p></body>"
                ),
            })}
          </script>
        </article>
      </body>
    </html>
    """

    class Response:
        status_code = 200
        text = html

    monkeypatch.setattr("router.yahoo_news.yahoo_news_router.requests.get", lambda *args, **kwargs: Response())
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda *args, **kwargs: None)

    entry = FeedItem()
    metadata = Metadata(title="Brazil unveils fuel subsidies", link=article_url)

    build_router()._get_article_content(metadata, entry)

    assert "STORY: Brazil said Wednesday" in entry.description
    assert "stalled in Congress" in entry.description
    assert "Short teaser paragraph" not in entry.description
    assert '<img src="https://example.com/thumbnail.jpg" />' in entry.description


def test_get_article_content_keeps_single_json_ld_paragraph(monkeypatch):
    article_url = "https://www.yahoo.com/news/videos/single-paragraph.html"
    html = f"""
    <html>
      <body>
        <article>
          <script type="application/ld+json">
            {json.dumps({
                "@type": "NewsArticle",
                "description": (
                    "<body><p>This single transcript paragraph is long enough to be useful "
                    "and should not be discarded just because it is the only body part.</p></body>"
                ),
            })}
          </script>
        </article>
      </body>
    </html>
    """

    class Response:
        status_code = 200
        text = html

    monkeypatch.setattr("router.yahoo_news.yahoo_news_router.requests.get", lambda *args, **kwargs: Response())
    monkeypatch.setattr("utils.feed_item_object.write_feed_item_to_cache", lambda *args, **kwargs: None)

    entry = FeedItem()
    metadata = Metadata(title="Single paragraph video", link=article_url)

    build_router()._get_article_content(metadata, entry)

    assert entry.description
    assert "This single transcript paragraph" in entry.description
