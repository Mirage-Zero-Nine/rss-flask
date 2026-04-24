import logging
from datetime import datetime
from bs4 import NavigableString

from router.base_router import BaseRouter
from router.zaobao.zaobao_realtime_router_constants import zaobao_realtime_page_suffix, zaobao_headers, \
    feed_title_mapping, feed_description_mapping, feed_prefix_mapping, zaobao_time_general_author, \
    zaobao_link, zaobao_region_general_title, zaobao_realtime_frontpage_prefix, zaobao_news_china_page_prefix, \
    zaobao_news_world_page_prefix
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix, FeedItem
from utils.get_link_content import get_link_content_with_header_and_empty_cookie, load_json_response
from utils.router_constants import language_chinese
from utils.tools import check_need_to_filter
from utils.xml_utilities import generate_feed_object_for_new_router


class ZaobaoRealtimeRouter(BaseRouter):
    PAGE_CONTENT_REGION_KEYS = {
        "china": {"news_china"},
        "world": {"news_world"},
    }

    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        # list of metadata of the articles
        metadata_list = []
        region = parameter["region"] if parameter else None

        for x in range(3):
            link = self.__build_articles_list_link(region, x)
            logging.info("Fetching Zaobao article list from %s", link)
            response = load_json_response(link, headers=zaobao_headers, cookies={})
            articles = self.__extract_articles_from_response(response, region)

            for article in articles:
                title = article['title']
                article_link = zaobao_link + article['href']
                timestamp = article['timestamp']

                if check_need_to_filter(link, title, link_filter, title_filter) is False:
                    # example: https://www.zaobao.com.sg/realtime/china/story20240612-3918781
                    cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
                    metadata = Metadata(title=title,
                                        link=article_link,
                                        cache_key=generate_cache_key(prefix=cache_prefix, name=article_link),
                                        created_time=timestamp)
                    metadata_list.append(metadata)

        return metadata_list

    def __build_articles_list_link(self, region, page_index):
        if region == "china":
            return zaobao_news_china_page_prefix + zaobao_realtime_page_suffix + str(page_index)

        if region == "world":
            return zaobao_news_world_page_prefix + zaobao_realtime_page_suffix + str(page_index)

        return self.articles_link + zaobao_realtime_page_suffix + str(page_index)

    def __extract_articles_from_response(self, response, region):
        response_body = response.get('response', {})
        direct_articles = response_body.get('articles')
        if isinstance(direct_articles, list):
            logging.info("Zaobao response for %s contains direct articles: %s", region, len(direct_articles))
            return direct_articles

        page_content_list = response_body.get('pageContentList')
        if not isinstance(page_content_list, list):
            logging.warning("Zaobao response for %s does not contain direct articles or pageContentList", region)
            return []

        matching_keys = self.PAGE_CONTENT_REGION_KEYS.get(region, set())
        selected_articles = []
        for section in page_content_list:
            section_key = section.get('key')
            section_articles = section.get('articles')
            if not isinstance(section_articles, list):
                continue
            if matching_keys and section_key not in matching_keys:
                continue
            selected_articles.extend(section_articles)

        logging.info(
            "Zaobao response for %s contains pageContentList; selected %s article(s) from keys %s",
            region or "all",
            len(selected_articles),
            ",".join(sorted(matching_keys)) if matching_keys else "all"
        )
        return selected_articles

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        logging.info("Fetching Zaobao article content for %s", article_metadata.link)
        soup = get_link_content_with_header_and_empty_cookie(article_metadata.link, zaobao_headers)
        meta_image = soup.find('meta', property='og:image')

        if entry.description is None:
            entry.description = ""

        if meta_image and meta_image.get('content'):
            image_url = meta_image['content']
            if image_url != "https://www.zaobao.com.sg/_web2/assets/social-share.png":
                img_tag = soup.new_tag('img', src=image_url)
                entry.description += str(img_tag)

        article_root = soup.find('article', class_='max-w-full')
        soup = article_root.find('div', class_='articleBody') if article_root else None

        if soup is None:
            logging.error(
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Getting empty page: {article_metadata.link}")
            entry.created_time = datetime.fromtimestamp(article_metadata.created_time)
            entry.author = zaobao_time_general_author
            if not entry.description:
                entry.description = "<p>Article content unavailable from upstream source.</p>"
            else:
                entry.description += "<p>Article content unavailable from upstream source.</p>"
            entry.persist_to_cache(self.router_path)
            return entry

        entry.created_time = datetime.fromtimestamp(article_metadata.created_time)
        ads = soup.find_all('div', class_=['google-ad', 'bff-google-ad'])
        for ad in ads:
            ad.extract()

        irrelevant = soup.find_all('div', class_='bff-recommend-article')
        for div in irrelevant:
            div.extract()

        related_sections = soup.find_all(['section', 'div'], class_=['related-topics-wrapper', 'related-articles', 'article-tags'])
        for section in related_sections:
            section.extract()

        unwanted_phrases = ('延伸阅读', '购买此文章', '上一篇', '下一篇', '热门', '更多消息', '最新')
        for element in soup.find_all(['section', 'div', 'aside', 'nav', 'h2', 'h3', 'p', 'a']):
            text = element.get_text(" ", strip=True)
            if any(phrase in text for phrase in unwanted_phrases):
                element.extract()

        img_tags = soup.find_all('img', {'data-src': True})
        for img_tag in img_tags:
            img_tag.attrs = {'src': img_tag['data-src']}

        main_content_parts = []
        allowed_tags = {'p', 'figure', 'img', 'blockquote', 'ul', 'ol'}
        for child in soup.children:
            if isinstance(child, NavigableString):
                continue

            if child.name in allowed_tags:
                if child.get_text(" ", strip=True) in unwanted_phrases:
                    continue
                main_content_parts.append(str(child))
                continue

            nested_allowed = child.find_all(allowed_tags, recursive=True)
            for nested in nested_allowed:
                if nested.get_text(" ", strip=True) in unwanted_phrases:
                    continue
                main_content_parts.append(str(nested))

        entry.description += "".join(main_content_parts)
        logging.info("Built Zaobao article content for %s", article_metadata.link)
        logging.debug("Zaobao article content for %s: %s", article_metadata.link, entry.description)
        entry.author = zaobao_time_general_author
        entry.persist_to_cache(self.router_path)

        return entry

    def _generate_response(self, last_build_time, feed_entries_list, parameter=None):
        region = parameter['region'] if parameter else None
        feed_title = feed_title_mapping.get(region, zaobao_region_general_title)
        feed_description = feed_description_mapping.get(
            region,
            "即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。"
        )
        feed_original_link = feed_prefix_mapping.get(region, zaobao_realtime_frontpage_prefix)
        feed = generate_feed_object_for_new_router(
            title=feed_title,
            link=feed_original_link,
            description=feed_description,
            language=language_chinese,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list
        )

        return feed
