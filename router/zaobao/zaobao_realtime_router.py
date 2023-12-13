import logging
import os
from datetime import datetime

from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix, \
    read_feed_item_from_json, FeedItem
from router.base_router import BaseRouter
from router.zaobao.zaobao_realtime_router_constants import zaobao_realtime_page_suffix, zaobao_headers, \
    zaobao_story_prefix, zaobao_time_convert_pattern, unwanted_div_id, unwanted_div_class, feed_title_mapping, \
    feed_description_mapping, feed_prefix_mapping, zaobao_time_general_author
from utils.get_link_content import get_link_content_with_bs_and_header
from utils.router_constants import html_parser, language_chinese
from utils.time_converter import convert_time_with_pattern
from utils.tools import check_need_to_filter
from utils.xml_utilities import generate_feed_object_for_new_router


class ZaobaoRealtimeRouter(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=""):
        # list of metadata of the articles
        metadata_list = []

        for x in range(2):  # get 2 pages, each page contains 24 items
            link = self.articles_link + parameter + zaobao_realtime_page_suffix + str(x)
            soup = get_link_content_with_bs_and_header(link,
                                                       html_parser,
                                                       zaobao_headers)
            news_list = soup.find_all(
                "div",
                {"class": "col col-lg-12"}
            )  # type is bs4.element.ResultSet

            for news in news_list:
                title = news.find('a').contents[0].text
                link = zaobao_story_prefix + news.find('a')['href']
                if check_need_to_filter(link, title, link_filter, title_filter) is False:
                    save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                    metadata = Metadata(title=title,
                                        link=link,
                                        json_name=generate_json_name(prefix=save_json_path_prefix, name=link))
                    metadata_list.append(metadata)

        return metadata_list

    def _get_individual_article(self, article_metadata, parameter=None):

        if os.path.exists(article_metadata.json_name):
            entry = read_feed_item_from_json(article_metadata.json_name)
        else:
            logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Getting content for: {article_metadata.link}")
            entry = FeedItem(title=article_metadata.title,
                             link=article_metadata.link,
                             guid=article_metadata.link)
            soup = get_link_content_with_bs_and_header(article_metadata.link,
                                                       html_parser, zaobao_headers).find('article', class_='article')
            if soup is None:
                logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Getting empty page: {article_metadata.link}")
                return entry

            # Find the element containing the publication date and time
            timestamp_text = soup.find('div', class_='story-postdate').text.strip().replace('发布 / ', '')
            entry.created_time = convert_time_with_pattern(timestamp_text,
                                                           zaobao_time_convert_pattern,
                                                           8)
            sections = soup.find_all('section')
            for section in sections:
                section.extract()

            for script_tag in soup.find_all('script'):
                script_tag.extract()

            for h1_element in soup.find_all('h1'):
                h1_element.extract()

            for id_name in unwanted_div_id:
                for element in soup.find_all('div', id=id_name):
                    element.extract()

            for class_name in unwanted_div_class:
                for element in soup.find_all('div', class_=class_name):
                    element.extract()

            img_tags = soup.find_all('img', {'data-src': True})
            for img_tag in img_tags:
                # Replace data-src with src and remove all other attributes
                img_tag.attrs = {'src': img_tag['data-src']}

            entry.description = soup
            entry.author = zaobao_time_general_author
            entry.save_to_json(self.router_path)

        return entry

    def _generate_response(self, last_build_time, feed_entries_list, parameter=None):
        feed_title = feed_title_mapping.get(parameter)
        feed_description = feed_description_mapping.get(parameter)
        feed_original_link = feed_prefix_mapping.get(parameter)
        feed = generate_feed_object_for_new_router(
            title=feed_title,
            link=feed_original_link,
            description=feed_description,
            language=language_chinese,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list
        )

        return feed
