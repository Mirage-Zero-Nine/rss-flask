import logging
from email.utils import parsedate_to_datetime
from html import escape
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from router.base_router import BaseRouter
from utils.feed_item_object import FeedItem, Metadata, convert_router_path_to_cache_prefix, generate_cache_key
from utils.log_context import log_external_fetch
from utils.router_constants import html_parser


class OpenAINewsRouter(BaseRouter):
    _REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    VALID_CATEGORIES = {
        "all": None,
        "company": "Company",
        "research": "Research",
        "product": "Product",
        "safety": "Safety",
        "engineering": "Engineering",
        "security": "Security",
        "global-affairs": "Global Affairs",
        "ai-adoption": "AI Adoption",
    }

    def warm_all_categories(self):
        for category in self.VALID_CATEGORIES:
            self.warm_cache(parameter={"category": category})

    def refresh_all_categories(self):
        for category in self.VALID_CATEGORIES:
            self.refresh_cache(parameter={"category": category})

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        category = (parameter or {}).get("category")
        if category not in self.VALID_CATEGORIES:
            logging.warning("Router %s called with invalid OpenAI news category=%s", self.router_path, category)
            return []

        expected_category = self.VALID_CATEGORIES[category]
        log_external_fetch("feedparser.parse", self.articles_link)
        parsed_feed = feedparser.parse(self.articles_link)
        if not parsed_feed.entries:
            logging.warning(
                "Router %s OpenAI news RSS has 0 entries (bozo=%s, bozo_exception=%s)",
                self.router_path,
                parsed_feed.get("bozo", False),
                parsed_feed.get("bozo_exception"),
            )
            return []

        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        metadata_list = []
        for entry in parsed_feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            if not title or not link:
                continue

            entry_categories = self._entry_categories(entry)
            if expected_category and expected_category not in entry_categories:
                continue

            summary = entry.get("summary", "")
            metadata_list.append(
                Metadata(
                    title=title,
                    link=link,
                    author="OpenAI",
                    guid=entry.get("id", link),
                    created_time=self._parse_feed_datetime(entry.get("published")),
                    cache_key=generate_cache_key(cache_prefix, link),
                    flag={
                        "summary": summary,
                        "categories": sorted(entry_categories),
                    },
                )
            )

        logging.info(
            "Router %s OpenAI news category=%s built %d metadata entries from %d RSS entries",
            self.router_path,
            category,
            len(metadata_list),
            len(parsed_feed.entries),
        )
        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        flag = article_metadata.flag if isinstance(article_metadata.flag, dict) else {}
        summary = flag.get("summary", "")
        categories = flag.get("categories", [])

        parts = self._extract_article_page_content(article_metadata.link)
        if not parts:
            logging.warning(
                "Router %s falling back to OpenAI RSS summary for link=%s",
                self.router_path,
                article_metadata.link,
            )
            parts = self._build_summary_parts(article_metadata.created_time, categories, summary)

        entry.author = article_metadata.author or "OpenAI"
        entry.created_time = article_metadata.created_time
        entry.description = "\n".join(parts) if parts else ""
        entry.persist_to_cache(self.router_path)

    def _extract_article_page_content(self, link):
        if not link:
            return []

        try:
            logging.debug("Router %s fetching OpenAI article page link=%s", self.router_path, link)
            response = requests.get(link, headers=self._REQUEST_HEADERS, timeout=15)
            logging.debug(
                "Router %s OpenAI article fetch status=%d length=%d link=%s",
                self.router_path,
                response.status_code,
                len(response.text),
                link,
            )
            if response.status_code != 200:
                return []
        except Exception:
            logging.exception("Router %s failed to fetch OpenAI article page link=%s", self.router_path, link)
            return []

        soup = BeautifulSoup(response.text, html_parser)
        container = soup.find("main") or soup.find("article") or soup.body
        if not container:
            return []

        for tag in container.find_all(["script", "style", "svg", "button", "nav", "footer", "header", "aside", "form", "noscript"]):
            tag.decompose()

        parts = []
        media = self._extract_media_block(container, link)
        if media:
            parts.append(media)

        share_text = container.find(string=lambda text: text and text.strip() == "Share")
        h1 = container.find("h1")
        seen_text = set()
        emitted_lists = set()
        for tag in container.find_all(["p", "h2", "h3", "ul", "ol"]):
            if share_text:
                if not tag.find_previous(string=lambda text: text and text.strip() == "Share"):
                    continue
            elif h1 and tag.find_previous("h1") != h1:
                continue

            text = " ".join(tag.get_text(" ", strip=True).split())
            if not text or text in seen_text:
                continue
            if self._is_article_chrome_text(text):
                if text in {"Author", "Keep reading"}:
                    break
                continue
            if tag.name in {"ul", "ol"}:
                tag_id = id(tag)
                if tag_id in emitted_lists:
                    continue
                emitted_lists.add(tag_id)

            seen_text.add(text)
            parts.append(self._clean_fragment(tag, link))

        return parts

    def _extract_media_block(self, container, base_url):
        iframe = container.find("iframe", src=True)
        image = container.find("img", src=True) or container.find("img", srcset=True)
        media = iframe or image
        if not media:
            return ""

        block = media
        for parent in media.parents:
            if parent == container:
                break
            if parent.name == "div" and (parent.find("iframe") or parent.find("img")):
                if parent.find(["h1", "h2", "h3", "p", "a"]):
                    continue
                block = parent

        if block == media and iframe and image:
            return f"<div>{self._clean_fragment(iframe, base_url)}{self._clean_fragment(image, base_url)}</div>"
        return self._clean_fragment(block, base_url)

    def _clean_fragment(self, tag, base_url):
        soup = BeautifulSoup(str(tag), html_parser)
        for unwanted in soup.find_all(["script", "style", "svg", "button", "noscript"]):
            unwanted.decompose()

        allowed_attrs = {
            "a": {"href"},
            "img": {"src", "srcset", "alt", "loading"},
            "iframe": {"src", "width", "height", "title", "allow", "allowfullscreen"},
        }
        for child in soup.find_all(True):
            attrs = dict(child.attrs)
            child.attrs.clear()
            for attr in allowed_attrs.get(child.name, set()):
                if attr in attrs:
                    value = attrs[attr]
                    if attr in {"href", "src"}:
                        value = urljoin(base_url, value)
                    child.attrs[attr] = value
            if child.name == "iframe" and "allowfullscreen" not in child.attrs:
                child.attrs["allowfullscreen"] = "allowfullscreen"

        return str(soup)

    @staticmethod
    def _build_summary_parts(created_time, categories, summary):
        parts = []
        if created_time:
            parts.append(f"<p>{created_time}</p>")
        if categories:
            parts.append(f"<p>{', '.join(escape(str(category)) for category in categories)}</p>")
        if summary:
            parts.append(f"<p>{escape(str(summary))}</p>")
        return parts

    @staticmethod
    def _is_article_chrome_text(text):
        chrome_text = {
            "Table of contents",
            "Loading...",
            "Loading…",
            "Share",
            "View all",
            "Our Research",
            "Latest Advancements",
            "Safety",
            "ChatGPT",
            "API Platform",
            "For Business",
            "Company",
            "Support",
            "More",
            "Terms & Policies",
            "Author",
            "Keep reading",
        }
        return text in chrome_text or text.startswith("(opens in a new window)")

    @staticmethod
    def _entry_categories(entry):
        return {
            tag.get("term")
            for tag in entry.get("tags", [])
            if tag.get("term")
        }

    @staticmethod
    def _parse_feed_datetime(value):
        if not value:
            return None

        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            logging.warning("Unable to parse OpenAI news published time: %s", value)
            return None
