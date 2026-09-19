import json
import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from router.router_for_rss_feed import RouterForRssFeed
from utils.cache_store import read_feed_item_from_cache, write_feed_item_to_cache
from utils.feed_item_object import FeedItem, Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.safe_http import safe_parse_feed


def _parse_feed_date(value: datetime | str | None) -> datetime | None:
    """Parse RSS and Atom dates, including Apple's date-only JSON-LD values."""
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        raw = value.strip()
        try:
            parsed = parsedate_to_datetime(raw)
        except (ValueError, TypeError):
            # Apple also publishes datePublished as YYYY-MM-DDZ.
            if raw.endswith("Z"):
                raw = raw[:-1] + ("+00:00" if "T" in raw else "")
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _article_publication_date(soup: BeautifulSoup) -> datetime | None:
    """Read the article's publication date, never its modification date."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            pending = [json.loads(script.get_text())]
        except (ValueError, TypeError):
            continue
        while pending:
            node = pending.pop()
            if isinstance(node, list):
                pending.extend(node)
            elif isinstance(node, dict):
                types = node.get("@type", [])
                if isinstance(types, str):
                    types = [types]
                if isinstance(types, list) and any(t in {"NewsArticle", "Article"} for t in types if isinstance(t, str)):
                    published = _parse_feed_date(node.get("datePublished"))
                    if published:
                        return published
                graph = node.get("@graph")
                if isinstance(graph, (list, dict)):
                    pending.append(graph)
    # Some Newsroom updates omit NewsArticle JSON-LD but show a dated byline.
    byline_date = soup.select_one(".category-eyebrow__date")
    if byline_date is not None:
        try:
            return datetime.strptime(
                byline_date.get_text(" ", strip=True), "%B %d, %Y"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None


class AppleNewsRouter(RouterForRssFeed):

    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        """Override to store RSS description in Metadata.flag for no per-article fetch."""
        metadata_list = []
        parse_feed = safe_parse_feed(self.articles_link)
        if not parse_feed.entries:
            logging.warning("Router %s RSS feed has 0 entries from %s", self.router_path, self.articles_link)
            return metadata_list

        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        for entry in parse_feed.entries:
            if entry.link and entry.title:
                metadata = Metadata(
                    title=entry.title,
                    link=entry.link,
                    created_time=_parse_feed_date(entry.get("published")) or _parse_feed_date(entry.get("updated")),
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
        """Parse Atom dates, falling back to updated when published is absent."""
        metadata_list = []
        parse_feed = safe_parse_feed(self.articles_link)
        if not parse_feed.entries:
            logging.warning("Router %s RSS feed has 0 entries from %s", self.router_path, self.articles_link)
            return metadata_list

        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        for entry in parse_feed.entries:
            if entry.link and entry.title:
                metadata = Metadata(
                    title=entry.title.strip(),
                    link=entry.link,
                    created_time=_parse_feed_date(entry.get("published")) or _parse_feed_date(entry.get("updated")),
                    cache_key=generate_cache_key(prefix=cache_prefix, name=entry.link),
                )
                metadata_list.append(metadata)

        logging.info("Router %s built %d articles from RSS feed", self.router_path, len(metadata_list))
        return metadata_list

    def _get_article(self, article_metadata: Metadata) -> FeedItem:
        """Repair legacy cached dates during refresh without replacing content."""
        cached = read_feed_item_from_cache(article_metadata.cache_key)
        if cached and cached.get("description") and not _parse_feed_date(cached.get("created_time")):
            created_time = _parse_feed_date(article_metadata.created_time)
            try:
                soup = get_link_content_with_bs_no_params(article_metadata.link)
                if soup is not None:
                    created_time = _article_publication_date(soup) or created_time
            except Exception as exc:
                logging.warning("Router %s could not recover article date for %s: %s",
                                self.router_path, article_metadata.link, exc)
            if created_time:
                updated = dict(cached, created_time=created_time.isoformat())
                write_feed_item_to_cache(article_metadata.cache_key, updated)
                article_metadata.created_time = created_time
                logging.info("Router %s repaired cached publication date link=%s date=%s",
                             self.router_path, article_metadata.link, created_time.isoformat())
        return super()._get_article(article_metadata)

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

        # Sections to exclude from output
        _exclude_classes = {"sosumi", "legal-info", "docsanddownloads", "presscontacts", "nr-article-share"}

        parts = []
        for child in article.children:
            if not hasattr(child, "name") or not child.name:
                continue
            classes = child.get("class", [])
            if _exclude_classes & set(classes):
                continue
            if "pagebody" in classes:
                for el in child.find_all(["h2", "div"], class_=["pagebody-header", "pagebody-copy"]):
                    # Remove footnote superscripts
                    for sup in el.find_all("sup"):
                        sup.decompose()
                    # Remove class attributes from all tags
                    for tag in el.find_all(True):
                        del tag["class"]
                    if el.name == "h2":
                        text = el.get_text(strip=True)
                        if text:
                            parts.append(f"<h2>{text}</h2>")
                    else:
                        # If content starts with a block element, output directly
                        block_child = el.find(["ul", "ol", "table", "blockquote"], recursive=False)
                        if block_child:
                            parts.append(str(block_child))
                        else:
                            inner = el.decode_contents().strip()
                            if inner:
                                parts.append(f"<p>{inner}</p>")
            elif child.name == "figure" or "image" in classes or "gallery" in classes:
                for img in child.find_all("img"):
                    src = img.get("src", "")
                    if src:
                        parts.append(f'<img src="{src}" />')

        entry.description = "\n".join(parts) if parts else ""
        entry.created_time = _article_publication_date(soup) or _parse_feed_date(article_metadata.created_time)
        article_metadata.created_time = entry.created_time
        entry.persist_to_cache(self.router_path)
