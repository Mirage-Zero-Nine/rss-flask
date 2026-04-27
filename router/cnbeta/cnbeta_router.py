from router.base_router import BaseRouter
from router.cnbeta.cnbeta_router_constants import cnbeta_query_page_count, cnbeta_articles_link, \
    cnbeta_news_router_author
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.get_link_content import get_link_content_with_utf8_decode
from utils.time_converter import convert_time_with_pattern
import logging


class CnbetaRouter(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        articles_list = []

        for i in range(0, cnbeta_query_page_count):
            page_url = f"{self.articles_link}/list/latest_{i + 1}.htm"
            logging.debug("Fetching page: %s", page_url)
            soup = get_link_content_with_utf8_decode(page_url)

            if not soup:
                logging.error("Failed to get soup for page: %s", page_url)
                continue

            ul_element = soup.find('ul', class_='info_list')
            if not ul_element:
                logging.error("Could not find 'ul' with class='info_list' on page: %s", page_url)
                continue

            txt_area_divs = ul_element.find_all('div', class_='txt_area')
            logging.debug("Found %d txt_area divs on page: %s", len(txt_area_divs), page_url)

            for div in txt_area_divs:
                a_tag = div.find('a')
                if not a_tag:
                    continue
                href = a_tag.get('href')
                title_element = a_tag.find('p', class_='txt_detail')
                title = title_element.text if title_element else None
                link = cnbeta_articles_link + href
                cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
                if link and title:
                    logging.debug("Found article: %s (%s)", title, link)
                    metadata = Metadata(title=title,
                                        link=link,
                                        cache_key=generate_cache_key(prefix=cache_prefix, name=link))
                    articles_list.append(metadata)

        if not articles_list:
            logging.warning(
                "Router %s found 0 articles from cnbeta after fetching %d pages",
                self.router_path, cnbeta_query_page_count,
            )
        else:
            logging.info("Total articles found in cnbeta: %d", len(articles_list))
        return articles_list

    def _get_article_content(self, article_metadata, entry):
        logging.info("Fetching content for: %s", article_metadata.link)

        soup = get_link_content_with_utf8_decode(article_metadata.link)
        if not soup:
            logging.error("Failed to get soup for: %s", article_metadata.link)
            return entry

        time_object = self.__extract_time(soup)
        logging.debug("Extracted time: %s", time_object)
        entry.created_time = convert_time_with_pattern(time_object, '%Y-%m-%d %H:%M:%S', 8)

        summary = self.__extract_summary(soup)
        content = self.__extract_content(soup)
        logging.debug("Extracted summary length: %d, content length: %d", len(summary), len(content))
        entry.description = summary + content
        if not entry.description:
            logging.warning("Router %s extracted empty description for %s (summary=%d, content=%d)",
                            self.router_path, article_metadata.link, len(summary), len(content))

        entry.author = cnbeta_news_router_author  # they don'don't have a specific author

        entry.persist_to_cache(self.router_path)
        logging.info("Successfully processed content for: %s", article_metadata.link)
        return entry

    @staticmethod
    def __extract_time(soup):
        time_element = soup.find('time', class_='time')
        if time_element is None:
            logging.warning("cnbeta could not find time element in page")
        return time_element.get_text() if time_element else None

    @staticmethod
    def __extract_summary(soup):
        article_summary_div = soup.find('div', class_='article-summ')
        return article_summary_div.decode_contents() if article_summary_div else ""

    @staticmethod
    def __extract_content(soup):
        article_cont_div = soup.find('div', class_='articleCont')
        return article_cont_div.decode_contents() if article_cont_div else ""
