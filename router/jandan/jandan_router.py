import re
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse

from router.base_router import BaseRouter
from router.jandan.jandan_constant import jandan_headers
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.get_link_content import get_link_content_with_header_and_empty_cookie
from utils.router_constants import html_parser
from utils.time_converter import convert_time_with_pattern
from utils.tools import remove_certain_tag


class JandanRouter(BaseRouter):
    def _normalize_article_link(self, link: str) -> str:
        return urljoin(f"{self.original_link.rstrip('/')}/", link)

    @staticmethod
    def _cache_identifier_for_link(link: str) -> str:
        parsed = urlparse(link)
        if parsed.hostname and parsed.hostname.endswith("jandan.net"):
            query = f"?{parsed.query}" if parsed.query else ""
            return f"{parsed.path}{query}"
        return link

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        """
        Override this method for each router.
        :return: list of articles
        """
        logging.info("JandanRouter fetching articles from %s", self.articles_link)
        soup = get_link_content_with_header_and_empty_cookie(self.articles_link, jandan_headers, html_parser)

        post_list = soup.find_all(
            "div",
            class_="post-item row"
        )  # type is bs4.element.ResultSet

        logging.info("JandanRouter found %d post-item row elements on %s", len(post_list), self.articles_link)

        metadata_list = []

        for i, post in enumerate(post_list):
            h2 = post.find('h2')
            if h2 is None:
                link_tag = post.find('a')
                link = link_tag['href'] if link_tag else '<no link>'
                post_text = post.get_text(strip=True)[:80]
                post_class = post.get('class', [])
                logging.info(
                    'JandanRouter post item %d has no h2 tag, skipping. link=%s class=%s text=%s',
                    i, link, post_class, post_text,
                )
                continue
            title = h2.text.strip()
            link_tag = h2.find('a')
            if link_tag is None:
                logging.warning("JandanRouter post item %d h2 has no link, skipping. title=%s", i, title[:60])
                continue
            raw_link = str(link_tag.get('href', '')).strip()
            if not raw_link:
                logging.warning("JandanRouter post item %d link is empty, skipping. title=%s", i, title[:60])
                continue
            link = self._normalize_article_link(raw_link)

            if "日好价" not in title:
                logging.debug("JandanRouter article %d: title=%s link=%s", i, title[:80], link)
                cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
                cache_identifier = self._cache_identifier_for_link(link)
                metadata_list.append(Metadata(
                    title=title,
                    link=link,
                    guid=link,
                    cache_key=generate_cache_key(prefix=cache_prefix, name=cache_identifier)
                ))
            else:
                logging.debug("JandanRouter skipping 日好价 item: %s", title[:60])

        logging.info("JandanRouter filtered to %d articles (excluded 日好价) from %s", len(metadata_list), self.articles_link)
        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        """
        Actual method to retrieve content
        :param article_metadata: metadata of article
        :param entry: object stores all the metadata and the content
        """
        logging.info("JandanRouter fetching content for %s", article_metadata.link)
        soup = get_link_content_with_header_and_empty_cookie(article_metadata.link, jandan_headers, html_parser)

        try:
            entry.author = soup.find("a", class_="post-author").get_text()
        except AttributeError:
            logging.warning("JandanRouter could not find post-author for %s, using default", article_metadata.link)
            entry.author = "煎蛋"

        try:
            post_meta = soup.find("div", class_="post-meta")
            if post_meta is None:
                logging.warning("JandanRouter could not find post-meta div for %s", article_metadata.link)
                raise AttributeError("no post-meta")
            create_time_string = post_meta.get_text(strip=True)
            create_time_string = re.sub(r"^[^0-9]*", "", create_time_string).strip()
            # Try multiple time formats since the site format can vary
            _time_patterns = [
                "%Y.%m.%d , %H:%M",
                "%Y.%m.%d @ %H:%M",
                "%Y.%m.%d %H:%M",
                "%Y-%m-%d , %H:%M",
                "%Y-%m-%d @ %H:%M",
                "%Y-%m-%d %H:%M",
            ]
            _parsed = None
            for _pat in _time_patterns:
                try:
                    _parsed = convert_time_with_pattern(create_time_string, _pat, 8)
                    break
                except ValueError:
                    continue
            if _parsed is None:
                raise ValueError(f"Unrecognized time format: {create_time_string!r}")
            entry.created_time = _parsed
        except Exception as e:
            logging.warning("JandanRouter time parsing failed for %s: %s, using now", article_metadata.link, e)
            entry.created_time = datetime.now()

        content = soup.find('div', class_='post-content')
        if content is None:
            logging.warning("JandanRouter could not find post-content div for %s", article_metadata.link)
            logging.warning("Router %s extracted empty content for %s", self.router_path, article_metadata.link)
            entry.description = ""
            entry.persist_to_cache(self.router_path, cache_key_override=article_metadata.cache_key)
            return

        remove_certain_tag(content, 'script')
        remove_certain_tag(content, 'h1')

        # Remove all ads (multiple adsbygoogle elements may exist)
        if content is not None:
            for ad in content.find_all("ins", class_="adsbygoogle"):
                ad.extract()

            # Remove promotional money.php image links
            for a in content.find_all("a", href=True):
                href = a.get("href", "")
                if "jandan.net/money.php" in href:
                    a.extract()
                    logging.debug("JandanRouter removed money.php promo link: %s", href)

        entry.description = content
        entry.persist_to_cache(self.router_path, cache_key_override=article_metadata.cache_key)
