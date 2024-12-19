import logging
from datetime import datetime

from router.base_router import BaseRouter
from router.zaobao.zaobao_realtime_router_constants import zaobao_realtime_page_suffix, zaobao_headers, unwanted_div_id, \
    unwanted_div_class, feed_title_mapping, feed_description_mapping, feed_prefix_mapping, zaobao_time_general_author, \
    zaobao_link
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix, FeedItem
from utils.get_link_content import get_link_content_with_header_and_empty_cookie, load_json_response
from utils.router_constants import language_chinese
from utils.tools import check_need_to_filter
from utils.xml_utilities import generate_feed_object_for_new_router


class ZaobaoRealtimeRouter(BaseRouter):

    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        # list of metadata of the articles
        metadata_list = []
        region = parameter["region"]

        for x in range(3):
            link = self.articles_link + region + zaobao_realtime_page_suffix + str(x)
            response = load_json_response(link, headers=zaobao_headers, cookies={})
            articles = response['response']['articles']

            for article in articles:
                title = article['title']
                article_link = zaobao_link + article['href']
                timestamp = article['timestamp']

                if check_need_to_filter(link, title, link_filter, title_filter) is False:
                    # example: https://www.zaobao.com.sg/realtime/china/story20240612-3918781
                    save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                    metadata = Metadata(title=title,
                                        link=article_link,
                                        json_name=generate_json_name(prefix=save_json_path_prefix, name=article_link),
                                        created_time=timestamp)
                    metadata_list.append(metadata)

        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        soup = get_link_content_with_header_and_empty_cookie(article_metadata.link, zaobao_headers)
        meta_image = soup.find('meta', property='og:image')

        if entry.description is None:
            entry.description = ""

        if meta_image and meta_image.get('content'):
            image_url = meta_image['content']
            if image_url != "https://www.zaobao.com.sg/_web2/assets/social-share.png":
                img_tag = soup.new_tag('img', src=image_url)
                entry.description += str(img_tag)

        soup = soup.find('article', class_='max-w-full').find('div', class_='articleBody')

        if soup is None:
            logging.error(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Getting empty page: {article_metadata.link}")
            return entry

        entry.created_time = datetime.fromtimestamp(article_metadata.created_time)
        ads = soup.find_all('div', class_=['google-ad', 'bff-google-ad'])
        for ad in ads:
            ad.extract()

        irrelevant = soup.find_all('div', class_='bff-recommend-article')
        for div in irrelevant:
            div.extract()

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

        entry.description += str(soup)
        entry.author = zaobao_time_general_author
        entry.save_to_json(self.router_path)

        return entry

    def _generate_response(self, last_build_time, feed_entries_list, parameter=None):
        region = parameter['region']
        feed_title = feed_title_mapping.get(region)
        feed_description = feed_description_mapping.get(region)
        feed_original_link = feed_prefix_mapping.get(region)
        feed = generate_feed_object_for_new_router(
            title=feed_title,
            link=feed_original_link,
            description=feed_description,
            language=language_chinese,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list
        )

        return feed
