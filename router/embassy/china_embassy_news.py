import logging
import re

from router.base_router import BaseRouter
from router.embassy.china_embassy_news_constants import china_embassy_news_prefix, china_embassy_news_author
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.get_link_content import get_link_content_with_urllib_request
from utils.time_converter import convert_time_with_pattern


class ChinaEmbassyNewsRouter(BaseRouter):
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
        for item in page:
            article = item.find('a')
            try:
                title = article.text
                link = article['href']
                if article != -1 and link_filter not in title:
                    if len(link) < 35:
                        link = china_embassy_news_prefix + link[1:]
                    cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
                    metadata_list.append(Metadata(
                        title=title,
                        link=link,
                        guid=link,
                        author=china_embassy_news_author,
                        cache_key=generate_cache_key(prefix=cache_prefix, name=link)
                    ))
            except AttributeError:
                continue

        if not metadata_list:
            logging.warning("Router %s extracted 0 articles from embassy page", self.router_path)
        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        """
        Actual method to retrieve content
        :param article_metadata: metadata of article
        :param entry: object stores all the metadata and the content
        """
        soup = get_link_content_with_urllib_request(article_metadata.link)
        time_div = soup.find("div", id="News_Body_Time")
        if time_div and time_div.get_text():
            entry.created_time = convert_time_with_pattern(time_div.get_text(), "%Y-%m-%d %H:%M")
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
            logging.warning("Router %s could not find News_Body_Txt_A div for %s", self.router_path, article_metadata.link)
        entry.description = desc_div
        if entry.description is None:
            logging.warning("Router %s description is None for %s", self.router_path, article_metadata.link)
        entry.persist_to_cache(self.router_path)
