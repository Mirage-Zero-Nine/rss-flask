import logging
import os

from utils.feed_item_object import FeedItem, convert_router_path_to_save_path_prefix, generate_json_name, Metadata, \
    read_feed_item_from_json
from router.base_router import BaseRouter
from router.cnbeta.cnbeta_router_constants import cnbeta_query_page_count, cnbeta_articles_link, \
    cnbeta_news_router_author
from utils.get_link_content import get_link_content_with_utf8_decode
from utils.time_converter import convert_time_with_pattern


class CnbetaRouter(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        articles_list = []

        for i in range(0, cnbeta_query_page_count):
            link = f"{self.articles_link}/list/latest_{i + 1}.htm"
            soup = get_link_content_with_utf8_decode(link)

            ul_element = soup.find('ul', class_='info_list')
            txt_area_divs = ul_element.find_all('div', class_='txt_area')

            for div in txt_area_divs:
                a_tag = div.find('a')
                href = a_tag.get('href')
                title = a_tag.find('p', class_='txt_detail').text if a_tag.find('p', class_='txt_detail') else None
                link = cnbeta_articles_link + href
                save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                if link and title:
                    metadata = Metadata(title=title,
                                        link=link,
                                        json_name=generate_json_name(prefix=save_json_path_prefix, name=link))
                    articles_list.append(metadata)

        return articles_list

    def _get_individual_article(self, article_metadata):
        if os.path.exists(article_metadata.json_name):
            entry = read_feed_item_from_json(article_metadata.json_name)
        else:
            logging.info(f"Getting content for: {article_metadata.link}")
            entry = FeedItem(title=article_metadata.title,
                             link=article_metadata.link,
                             guid=article_metadata.link)
            soup = get_link_content_with_utf8_decode(article_metadata.link)

            time_object = self.__extract_time(soup)
            entry.created_time = convert_time_with_pattern(time_object, '%Y-%m-%d %H:%M:%S', 8)

            entry.description = self.__extract_content(soup)

            entry.author = cnbeta_news_router_author  # they don't have a specific author

            entry.save_to_json(self.router_path)
        return entry

    @staticmethod
    def __extract_time(soup):
        time_element = soup.find('time', class_='time')
        return time_element.get_text() if time_element else None

    @staticmethod
    def __extract_content(soup):
        article_cont_div = soup.find('div', class_='articleCont')
        return article_cont_div.decode_contents() if article_cont_div else None
