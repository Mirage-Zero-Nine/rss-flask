import datetime as dt

from bs4 import BeautifulSoup

from router.dayone.day_one_blog_router import DayOneBlogRouter
from utils.feed_item_object import FeedItem, Metadata
from utils.router_constants import html_parser


def build_router():
    return DayOneBlogRouter(
        router_path="/dayone",
        feed_title="Day One Blog",
        original_link="https://dayoneapp.com/blog/",
        articles_link="https://dayoneapp.com/blog/",
        description="Day One Blog - Your Journal for Life",
        language="en-us",
    )


def test_get_articles_list_extracts_title_and_article_link(monkeypatch):
    listing = BeautifulSoup(
        """
        <h3 class="entry-title"><a href="https://dayoneapp.com/blog/journaling/">
          A title about journaling
        </a></h3>
        """,
        html_parser,
    )
    monkeypatch.setattr(
        "router.dayone.day_one_blog_router.get_link_content_with_bs_no_params",
        lambda *args, **kwargs: listing,
    )

    articles = build_router()._get_articles_list()

    assert len(articles) == 1
    assert articles[0].title.strip() == "A title about journaling"
    assert articles[0].link == "https://dayoneapp.com/blog/journaling/"
    assert articles[0].cache_key.startswith("router_cache:dayone:")


def test_article_content_restores_lazy_figure_image_and_keeps_content_metadata(monkeypatch):
    article_html = """
    <html><head><meta name="author" content="Morgan Lee"></head><body>
      <ul class="entry-meta"><li>June 18, 2026</li></ul>
      <div class="entry-content">
        <p style="color: red">The article begins with useful text.</p>
        <figure class="wp-block-image">
          <img src="data:image/gif;base64,placeholder" alt="loading"
               data-src="https://cdn.example.test/temporary.jpg" style="display:none">
          <noscript><img src="https://cdn.example.test/journal-page.jpg"
                         alt="A handwritten journal page" width="1200"></noscript>
          <figcaption>A page from the journal</figcaption>
        </figure>
        <figure><img src="https://cdn.example.test/ordinary.jpg" alt="Ordinary image"></figure>
        <p class="is-style-default has-background">Decorative callout to omit.</p>
        <div class="sharedaddy sd-sharing-enabled">Share controls to omit.</div>
        <p>The article continues after the image.</p>
      </div>
    </body></html>
    """
    soup = BeautifulSoup(article_html, html_parser)
    monkeypatch.setattr(
        "router.dayone.day_one_blog_router.get_link_content_with_bs_no_params",
        lambda *args, **kwargs: soup,
    )
    persisted = []
    monkeypatch.setattr(
        FeedItem,
        "persist_to_cache",
        lambda self, router_path: persisted.append((router_path, self)),
    )

    entry = FeedItem(title="A title about journaling", link="https://dayoneapp.com/blog/journaling/")
    build_router()._get_article_content(
        Metadata(title=entry.title, link=entry.link), entry
    )

    assert entry.title == "A title about journaling"
    assert entry.author == "Morgan Lee"
    assert entry.created_time == dt.datetime(2026, 6, 18, tzinfo=dt.timezone.utc)
    assert len(persisted) == 1
    assert persisted[0][0] == "/dayone"

    body = BeautifulSoup(str(entry.description), html_parser)
    figure = body.select_one("figure.wp-block-image")
    assert figure is not None
    # The figure's server-rendered placeholder is replaced by the nested noscript image.
    image = figure.select_one("img")
    assert image is not None
    assert image.attrs == {"src": "https://cdn.example.test/journal-page.jpg"}
    assert figure.select_one("noscript") is None
    assert "loading" not in str(figure)
    assert "temporary.jpg" not in str(figure)
    assert "A page from the journal" in str(figure)

    # A regular figure image remains intact, while inline styles and known clutter are removed.
    assert body.select_one('figure img[src="https://cdn.example.test/ordinary.jpg"]') is not None
    assert "style=" not in str(body)
    assert "Decorative callout" not in str(body)
    assert "Share controls" not in str(body)
    assert "The article begins with useful text." in body.get_text(" ", strip=True)
    assert "The article continues after the image." in body.get_text(" ", strip=True)
