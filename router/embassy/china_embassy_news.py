import logging
import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from router.base_router import BaseRouter
from router.embassy.china_embassy_news_constants import china_embassy_news_prefix, china_embassy_news_author
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.get_link_content import get_link_content_with_urllib_request
from utils.time_converter import convert_time_with_pattern


class ChinaEmbassyNewsRouter(BaseRouter):
    @staticmethod
    def _article_urls(link: str, base_url: str) -> tuple[str, str]:
        """Separate the verified fetch URL from the historical RSS identity.

        Relative links previously resolved to the HTTP .org hostname. Keep
        that exact logical identifier so HTTPS migration reuses existing Redis
        payloads and Reeder GUIDs; the identifier is never used for fetching.
        """
        absolute_url = urljoin(base_url.rstrip('/') + '/', link)
        parsed = urlsplit(absolute_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("Invalid embassy article URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("Embassy article URL contains credentials")
        if parsed.hostname in {"losangeles.china-consulate.org", "losangeles.china-consulate.gov.cn"}:
            if parsed.port not in {None, 80, 443}:
                raise ValueError("Unexpected embassy article URL port")
            fetch_url = urlunsplit(("https", "losangeles.china-consulate.gov.cn", parsed.path, parsed.query, parsed.fragment))
            legacy_guid = urlunsplit(("http", "losangeles.china-consulate.org", parsed.path, parsed.query, parsed.fragment))
            return fetch_url, legacy_guid
        return absolute_url, absolute_url

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        soup = get_link_content_with_urllib_request(self.articles_link)
        if soup is None:
            logging.warning("Router %s failed to fetch embassy page %s", self.router_path, self.articles_link)
            return []
        page = soup.find("ul", {"class": "tt"})
        if page is None:
            logging.warning("Router %s could not find 'ul.tt' on embassy page %s", self.router_path, self.articles_link)
            return []

        metadata_list = []
        for article in page.find_all('a', href=True):
            title = article.get_text()
            if link_filter and link_filter in title:
                continue
            try:
                link, guid = self._article_urls(str(article['href']), self.articles_link)
            except ValueError:
                logging.warning("Router %s skipped invalid embassy article URL", self.router_path)
                continue
            cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
            metadata_list.append(Metadata(
                title=title,
                link=link,
                guid=guid,
                author=china_embassy_news_author,
                cache_key=generate_cache_key(prefix=cache_prefix, name=guid)
            ))

        if not metadata_list:
            logging.warning("Router %s extracted 0 articles from embassy page", self.router_path)
        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        """
        Actual method to retrieve content
        :param article_metadata: metadata of article
        :param entry: object stores all the metadata and the content
        """
        fetch_url, legacy_guid = self._article_urls(article_metadata.link, china_embassy_news_prefix)
        soup = get_link_content_with_urllib_request(fetch_url)
        if soup is None:
            logging.warning("Router %s failed to fetch embassy article", self.router_path)
            return
        entry.link = fetch_url
        entry.guid = article_metadata.guid or legacy_guid
        time_div = soup.find("div", id="News_Body_Time")
        if time_div and time_div.get_text():
            entry.created_time = convert_time_with_pattern(time_div.get_text(), "%Y-%m-%d %H:%M")
        else:
            # Try YYYY/MM/DD HH:MM pattern (used on china-embassy.org pages)
            page_text = soup.get_text()
            slash_match = re.search(r"(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2})", page_text)
            if slash_match:
                entry.created_time = convert_time_with_pattern(slash_match.group(1), "%Y/%m/%d %H:%M")
            else:
                match = re.search(r"/(20\d{2})(\d{2})(\d{2})_", article_metadata.link)
                if match:
                    fallback = match.group(1) + match.group(2) + match.group(3)
                    entry.created_time = convert_time_with_pattern(fallback, "%Y%m%d", 0)
                    logging.info("Fallback to URL date %s for %s", fallback, article_metadata.link)
                else:
                    logging.warning("Failed to find publish time for %s", article_metadata.link)
        for tag in soup.find_all(True):
            tag.attrs = {key: val for key, val in tag.attrs.items() if key != 'style'}
        desc_div = soup.find('div', id='News_Body_Txt_A')
        if desc_div is None:
            desc_div = soup.find('div', class_='view_default')
        if desc_div is None:
            logging.warning("Router %s could not find content div for %s", self.router_path, article_metadata.link)
        entry.description = desc_div
        if not entry.description:
            logging.warning("Router %s description is None for %s", self.router_path, article_metadata.link)
        entry.persist_to_cache(self.router_path, cache_key_override=article_metadata.cache_key or None)
