import logging
from email.utils import parsedate_to_datetime

import feedparser

from router.router_for_rss_feed import RouterForRssFeed
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.get_link_content import get_link_content_with_bs_no_params


def _parse_feed_date(date_str):
    """Convert RSS/Atom date string to datetime, return None on failure."""
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        return None


class AppleNewsRouter(RouterForRssFeed):

    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        """Override to store RSS description in Metadata.flag for no per-article fetch."""
        metadata_list = []
        parse_feed = feedparser.parse(self.articles_link)
        if not parse_feed.entries:
            logging.warning("Router %s RSS feed has 0 entries from %s", self.router_path, self.articles_link)
            return metadata_list

        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        for entry in parse_feed.entries:
            if entry.link and entry.title:
                metadata = Metadata(
                    title=entry.title,
                    link=entry.link,
                    created_time=_parse_feed_date(entry.get("published") or entry.get("updated")),
                    cache_key=generate_cache_key(prefix=cache_prefix, name=entry.link),
                    flag=entry.get("description", ""),
                )
                metadata_list.append(metadata)

        logging.info("Router %s built %d articles from RSS feed", self.router_path, len(metadata_list))
        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        """Use pre-built RSS description — no network call needed."""
        entry.description = article_metadata.flag
        entry.created_time = article_metadata.created_time
        entry.persist_to_cache(self.router_path)


class AppleNewsroomRouter(RouterForRssFeed):

    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        """Parse Atom feed, store created_time from 'updated' field."""
        metadata_list = []
        parse_feed = feedparser.parse(self.articles_link)
        if not parse_feed.entries:
            logging.warning("Router %s RSS feed has 0 entries from %s", self.router_path, self.articles_link)
            return metadata_list

        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        for entry in parse_feed.entries:
            if entry.link and entry.title:
                metadata = Metadata(
                    title=entry.title.strip(),
                    link=entry.link,
                    created_time=_parse_feed_date(entry.get("published") or entry.get("updated")),
                    cache_key=generate_cache_key(prefix=cache_prefix, name=entry.link),
                )
                metadata_list.append(metadata)

        logging.info("Router %s built %d articles from RSS feed", self.router_path, len(metadata_list))
        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        """Fetch full article content from the newsroom page."""
        soup = get_link_content_with_bs_no_params(article_metadata.link)
        if soup is None:
            logging.warning("Router %s failed to fetch article %s", self.router_path, article_metadata.link)
            return

        article = soup.find("article")
        if not article:
            logging.warning("Router %s no <article> tag found for %s", self.router_path, article_metadata.link)
            return

        parts = []
        for child in article.children:
            if not hasattr(child, "name") or not child.name:
                continue
            classes = child.get("class", [])
            if "pagebody" in classes:
                paragraphs = child.find_all("p")
                if not paragraphs:
                    paragraphs = child.find_all("div", class_="pagebody-copy")
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text:
                        parts.append(f"<p>{text}</p>")
            elif child.name == "figure" or "image" in classes or "gallery" in classes:
                for img in child.find_all("img"):
                    src = img.get("src", "")
                    if src:
                        parts.append(f'<img src="{src}" />')

        entry.description = "\n".join(parts) if parts else ""
        entry.created_time = article_metadata.created_time
        entry.persist_to_cache(self.router_path)
