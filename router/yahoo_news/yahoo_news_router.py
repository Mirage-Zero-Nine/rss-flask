import json
import logging
import re
import time
from html import unescape

import requests
from bs4 import BeautifulSoup

from router.base_router import BaseRouter
from utils.feed_item_object import FeedItem, Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.router_constants import html_parser


class YahooNewsRouter(BaseRouter):
    """Router for Yahoo News Reuters brand page with per-topic filtering."""

    VALID_TOPICS = {"world", "business", "celebrity", "politics", "health", "news", "u.s."}

    _REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_soup = None

    def _fetch_page(self, url, retries=1):
        """Fetch a page with browser-like headers. Retries once on non-200."""
        for attempt in range(1 + retries):
            logging.debug("Router %s fetching URL=%s attempt=%d", self.router_path, url, attempt + 1)
            try:
                resp = requests.get(url, headers=self._REQUEST_HEADERS, timeout=15)
                logging.debug("Router %s fetch URL=%s status=%d length=%d", self.router_path, url, resp.status_code, len(resp.text))
                if resp.status_code == 200:
                    return BeautifulSoup(resp.text, html_parser)
                logging.warning("Router %s fetch URL=%s returned status=%d", self.router_path, url, resp.status_code)
            except Exception:
                logging.exception("Router %s failed to fetch %s", self.router_path, url)
            if attempt < retries:
                time.sleep(2)
        return None

    def _remove_trading_disclosure_tags(self, article_tag):
        removed_count = 0
        while True:
            disclosure_text = article_tag.find(string=lambda text: text and text.strip() == "Trading disclosure")
            if not disclosure_text:
                return removed_count

            disclosure_tag = disclosure_text.find_parent("section", class_=lambda c: c and "ticker-list" in c)
            if not disclosure_tag:
                disclosure_tag = disclosure_text.find_parent("footer")
            if not disclosure_tag:
                disclosure_tag = disclosure_text.parent

            disclosure_tag.decompose()
            removed_count += 1

    def _iter_json_ld_objects(self, soup):
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            if isinstance(data, dict):
                if isinstance(data.get("@graph"), list):
                    for item in data["@graph"]:
                        if isinstance(item, dict):
                            yield item
                else:
                    yield data
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        yield item

    def _extract_json_ld_image_url(self, ld):
        thumbnail = ld.get("thumbnailUrl")
        if isinstance(thumbnail, list):
            thumbnail = next((url for url in thumbnail if isinstance(url, str)), "")
        if isinstance(thumbnail, str) and thumbnail:
            return thumbnail

        image = ld.get("image")
        if isinstance(image, str):
            return image
        if isinstance(image, dict):
            url = image.get("url")
            return url if isinstance(url, str) else ""
        if isinstance(image, list):
            for item in image:
                if isinstance(item, str):
                    return item
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    return item["url"]
        return ""

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        topic = (parameter or {}).get("topic")
        if not topic:
            logging.warning("Router %s _get_articles_list called without topic parameter", self.router_path)
            return []

        topic_lower = topic.lower()

        # Use cached soup if available (set by refresh_all_topics), otherwise fetch
        if self._cached_soup:
            logging.debug("Router %s using cached soup for topic '%s'", self.router_path, topic_lower)
            soup = self._cached_soup
        else:
            logging.info("Router %s fetching Yahoo Reuters page for topic '%s'", self.router_path, topic_lower)
            soup = self._fetch_page(self.articles_link)
            if soup is None:
                logging.error("Router %s failed to fetch Yahoo Reuters page for topic '%s'", self.router_path, topic_lower)
                return []

        return self._parse_articles_for_topic(soup, topic_lower)

    def _parse_articles_for_topic(self, soup, topic_lower):
        """Parse articles from soup for a specific topic."""
        pub_dates = {}
        ld_script = soup.find("script", type="application/ld+json")
        if ld_script:
            try:
                ld_data = json.loads(ld_script.string)
                for part in ld_data.get("hasPart", []):
                    url = part.get("url", "")
                    date = part.get("datePublished") or part.get("uploadDate")
                    if url and date:
                        pub_dates[url] = date
                logging.debug("Router %s parsed %d timestamps from JSON-LD", self.router_path, len(pub_dates))
            except (json.JSONDecodeError, TypeError):
                logging.warning("Router %s failed to parse JSON-LD for timestamps", self.router_path)

        strm = soup.find("div", id="strm")
        if not strm:
            logging.warning("Router %s could not find #strm section on page", self.router_path)
            return []

        links = strm.find_all("a", attrs={"data-ylk": lambda v: v and "elm:hdln" in v and "subsec:publisher-brand" in v})
        logging.debug("Router %s found %d headline links in #strm", self.router_path, len(links))

        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        metadata_list = []
        seen_titles = set()
        skipped_dedup = 0

        for link in links:
            ylk = link.get("data-ylk", "")
            cat_match = re.search(r"cnt_tpc:([^;]+)", ylk)
            if not cat_match:
                continue
            if cat_match.group(1).lower() != topic_lower:
                continue

            href = link.get("href", "")
            title = link.get_text(strip=True)
            if not href or not title:
                continue

            if title in seen_titles:
                skipped_dedup += 1
                logging.debug("Router %s dedup skipped: '%s'", self.router_path, title[:60])
                continue
            seen_titles.add(title)

            cache_key = generate_cache_key(cache_prefix, href)
            metadata = Metadata(
                title=title,
                link=href,
                author="Reuters",
                created_time=pub_dates.get(href),
                guid=href,
                cache_key=cache_key,
            )
            metadata_list.append(metadata)

        logging.info(
            "Router %s topic '%s': %d articles (%d duplicates removed)",
            self.router_path, topic_lower, len(metadata_list), skipped_dedup,
        )
        return metadata_list

    def refresh_all_topics(self):
        """Fetch the page once and refresh cache for all discovered topics."""
        logging.info("Router %s refresh_all_topics: fetching page from %s", self.router_path, self.articles_link)

        soup = self._fetch_page(self.articles_link)
        if soup is None:
            logging.error("Router %s refresh_all_topics: page fetch failed", self.router_path)
            return

        # Discover topics on the page
        strm = soup.find("div", id="strm")
        if not strm:
            logging.warning("Router %s refresh_all_topics: no #strm section found", self.router_path)
            return

        links = strm.find_all("a", attrs={"data-ylk": lambda v: v and "elm:hdln" in v and "subsec:publisher-brand" in v})
        logging.info("Router %s refresh_all_topics: found %d raw links in #strm", self.router_path, len(links))

        topics_found = set()
        topic_counts = {}
        for link in links:
            ylk = link.get("data-ylk", "")
            cat_match = re.search(r"cnt_tpc:([^;]+)", ylk)
            if cat_match:
                cat = cat_match.group(1).lower()
                topic_counts[cat] = topic_counts.get(cat, 0) + 1
                if cat in self.VALID_TOPICS:
                    topics_found.add(cat)

        logging.info("Router %s refresh_all_topics: category breakdown=%s", self.router_path, topic_counts)
        logging.info("Router %s refresh_all_topics: valid topics to refresh=%s", self.router_path, topics_found)

        # Cache the soup so _get_articles_list doesn't re-fetch
        self._cached_soup = soup
        try:
            for topic in topics_found:
                logging.info("Router %s refresh_all_topics: refreshing topic '%s'", self.router_path, topic)
                self.refresh_cache(parameter={"topic": topic}, force=True)
        finally:
            self._cached_soup = None
            logging.info("Router %s refresh_all_topics: completed for %d topics", self.router_path, len(topics_found))

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        logging.info("Router %s fetching article content title='%s' link=%s", self.router_path, article_metadata.title[:50], article_metadata.link)

        try:
            resp = requests.get(article_metadata.link, headers=self._REQUEST_HEADERS, timeout=15)
            logging.debug("Router %s article fetch status=%d length=%d link=%s", self.router_path, resp.status_code, len(resp.text), article_metadata.link)
            soup = BeautifulSoup(resp.text, html_parser)
        except Exception:
            logging.exception("Router %s failed to fetch article page for %s", self.router_path, article_metadata.link)
            entry.description = ""
            entry.persist_to_cache(self.router_path)
            return

        # Extract time
        time_text = ""
        time_tag = soup.find("time")
        if time_tag:
            time_text = time_tag.get_text(strip=True)
            if time_tag.get("datetime"):
                entry.created_time = time_tag["datetime"]

        # Extract author
        author_span = soup.find("span", class_=lambda c: c and "byline-attr-author" in c)
        if author_span:
            entry.author = author_span.get_text(strip=True)

        parts = []
        content_found = False
        if time_text:
            parts.append(f"<p>{time_text}</p>")

        article_tag = soup.find("article")
        if article_tag:
            removed_disclosure_count = self._remove_trading_disclosure_tags(article_tag)
            if removed_disclosure_count:
                logging.debug(
                    "Router %s removed %d trading disclosure tags from article link=%s",
                    self.router_path, removed_disclosure_count, article_metadata.link,
                )

            # Extract figures (images) from article
            figures = article_tag.find_all("figure")
            for fig in figures:
                img = fig.find("img")
                caption = fig.find("figcaption")
                if img and img.get("src"):
                    parts.append(f'<img src="{img["src"]}" />')
                    content_found = True
                    if caption:
                        parts.append(f"<p><em>{caption.get_text(strip=True)}</em></p>")

            # Extract paragraphs from article
            paragraphs = [p for p in article_tag.find_all("p") if len(p.get_text(strip=True)) > 20]
            for p in paragraphs:
                parts.append(f"<p>{p.get_text(strip=True)}</p>")
                content_found = True

            logging.debug(
                "Router %s article extracted %d figures, %d paragraphs from <article> tag link=%s",
                self.router_path, len(figures), len(paragraphs), article_metadata.link,
            )

        # Fallback for video pages: extract description from JSON-LD
        if not parts or len(parts) <= 1:
            logging.debug("Router %s no article body found, trying JSON-LD fallback link=%s", self.router_path, article_metadata.link)
            best_desc = ""
            best_thumb = ""
            for ld in self._iter_json_ld_objects(soup):
                image_url = self._extract_json_ld_image_url(ld)
                if image_url and not best_thumb:
                    best_thumb = image_url

                desc = ld.get("description", "")
                if isinstance(desc, str) and len(desc) > len(best_desc):
                    best_desc = desc
                    if image_url:
                        best_thumb = image_url

            if best_desc and len(best_desc) > 50:
                if best_thumb:
                    parts.insert(1, f'<img src="{best_thumb}" />')
                desc_soup = BeautifulSoup(best_desc, html_parser)
                desc_paragraphs = [p for p in desc_soup.find_all("p") if len(p.get_text(strip=True)) > 20]
                if desc_paragraphs:
                    for p in desc_paragraphs:
                        parts.append(f"<p>{p.get_text(strip=True)}</p>")
                    content_found = True
                else:
                    desc_text = unescape(desc_soup.get_text(" ", strip=True))
                    if len(desc_text) > 20:
                        parts.append(f"<p>{desc_text}</p>")
                        content_found = True
                logging.info(
                    "Router %s used JSON-LD fallback: %d paragraphs, thumbnail=%s link=%s",
                    self.router_path, len(desc_paragraphs), bool(best_thumb), article_metadata.link,
                )
            else:
                logging.warning("Router %s no content found for article link=%s", self.router_path, article_metadata.link)

        entry.description = "\n".join(parts) if content_found else ""
        logging.info(
            "Router %s article content cached: %d chars, title='%s'",
            self.router_path, len(entry.description), article_metadata.title[:50],
        )
        entry.persist_to_cache(self.router_path)
