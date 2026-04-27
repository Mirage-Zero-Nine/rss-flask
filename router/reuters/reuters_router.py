import json
import logging
import re
from datetime import datetime
from urllib.parse import quote, urljoin

import requests
from router.base_router import BaseRouter
from router.reuters.reuters_constants import (
    reuters_site_link,
    reuters_description,
)
from utils.cache_store import read_feed_item_from_cache
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix, FeedItem
from utils.log_context import log_external_fetch
from utils.router_constants import html_parser, language_english
from utils.time_converter import convert_time_with_pattern
from utils.xml_utilities import generate_feed_object_for_new_router
from utils.get_link_content import get_link_content_with_bs_no_params


class ReutersRouter(BaseRouter):
    """Reuters router."""

    @staticmethod
    def _fetch_with_requests(url: str, timeout: int = 30) -> dict:
        """Fetch URL using requests (standard HTTP)."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            status = response.status_code
            try:
                json_data = response.json()
            except ValueError:
                json_data = None
            return {'status': status, 'json': json_data, 'error': None}
        except requests.RequestException as e:
            logging.warning("Request error for %s: %s", url, e)
            return {'status': None, 'json': None, 'error': str(e)}

    @staticmethod
    def __resolve_created_time(article, cache_key):
        published_time = article.get("published_time")
        if published_time:
            try:
                return convert_time_with_pattern(published_time, "%Y-%m-%dT%H:%M:%S.%fZ").isoformat()
            except ValueError:
                try:
                    return convert_time_with_pattern(published_time, "%Y-%m-%dT%H:%M:%SZ").isoformat()
                except ValueError:
                    pass

        cached_entry = read_feed_item_from_cache(cache_key)
        cached_created_time = cached_entry.get("created_time") if cached_entry else None
        if cached_created_time:
            logging.warning(
                "Reuters article id=%s title=%s link=%s has invalid published_time=%s; reusing cached created_time=%s",
                article.get("id", "<unknown>"),
                article.get("title", "<missing>"),
                article.get("canonical_url", "<missing>"),
                published_time,
                cached_created_time,
            )
            return cached_created_time

        fallback_created_time = datetime(1970, 1, 1).isoformat()
        logging.warning(
            "Reuters article id=%s title=%s link=%s has invalid published_time=%s and no cached timestamp; using stable fallback=%s",
            article.get("id", "<unknown>"),
            article.get("title", "<missing>"),
            article.get("canonical_url", "<missing>"),
            published_time,
            fallback_created_time,
        )
        return fallback_created_time

    @staticmethod
    def __is_captcha_challenge(data):
        return isinstance(data, dict) and "url" in data and "captcha" in str(data.get("url", "")).lower()

    @staticmethod
    def __extract_reuters_result(data, context, response, json_query, resource_link=None) -> dict | None:
        if not isinstance(data, dict):
            logging.error(
                "Unexpected Reuters %s payload type. resource_link=%s status=%s url=%s query=%s payload_type=%s",
                context,
                resource_link,
                response.get('status'),
                resource_link,
                json_query,
                type(data).__name__,
            )
            return None

        if ReutersRouter.__is_captcha_challenge(data):
            logging.error(
                "Reuters %s blocked by captcha. resource_link=%s status=%s challenge_url=%s",
                context,
                resource_link,
                response.get('status'),
                data.get("url"),
            )
            return None

        result = data.get("result")
        if isinstance(result, dict):
            return result

        logging.error(
            "Reuters %s payload missing result object. resource_link=%s status=%s query=%s top_level_keys=%s",
            context,
            resource_link,
            response.get('status'),
            json_query,
            sorted(data.keys()),
        )
        return None

    @staticmethod
    def __build_api_request_link(root_url, json_query):
        return root_url + quote(json_query, safe="")

    def __build_section_link(self, category, topic=None):
        path = f"/{category}/{topic + '/' if topic else ''}"
        return urljoin(self.original_link, path)

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []
        category, topic, limit = parameter['category'], parameter['topic'], parameter['limit']

        logging.info(f"category: {category}, topic: {topic}, limit: {limit}")
        section_id = f"/{category}/{topic + '/' if topic else ''}"

        json_query = json.dumps({
            'offset': 0,
            'size': limit,
            'section_id': section_id,
            'website': 'reuters',
        })
        request_link = self.__build_api_request_link(self.articles_link, json_query)

        log_external_fetch(
            "requests",
            request_link,
            resource="reuters_articles_list",
        )

        response_data = self._fetch_with_requests(request_link)

        if response_data.get('error'):
            logging.error("Request error fetching articles list: %s", response_data['error'])
            return []

        if response_data.get('status') != 200:
            logging.error("Reuters API returned status=%s for articles list", response_data.get('status'))
            return []

        data = response_data.get('json')
        if not data:
            logging.error("Reuters articles list response is empty")
            return []

        result = self.__extract_reuters_result(
            data=data,
            context="articles list",
            response=response_data,
            json_query=json_query,
            resource_link=request_link,
        )
        if result is None:
            return []
        articles = result.get("articles", [])
        if not articles:
            logging.warning("Reuters returned 0 articles for category=%s topic=%s", category, topic)
            return []

        for article in articles:
            article_id = article.get('id', '')
            canonical_url = article.get('canonical_url', '')
            cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
            cache_key = generate_cache_key(prefix=cache_prefix, name=article_id)
            created_time = self.__resolve_created_time(article, cache_key)

            metadata_list.append(Metadata(
                title=article.get('title', ''),
                link=canonical_url,
                guid=article_id,
                created_time=created_time,
                cache_key=cache_key,
            ))

        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        article_id = article_metadata.guid
        json_query = json.dumps({
            'article_ids': [article_id],
            'website': 'reuters',
        })
        request_link = self.__build_api_request_link(self.articles_link, json_query)

        log_external_fetch(
            "requests",
            request_link,
            resource="reuters_article_content",
            article_link=article_metadata.link,
        )

        response_data = self._fetch_with_requests(request_link)

        if response_data.get('error'):
            logging.error("Request error fetching article content: %s", response_data['error'])
            self.__fetch_article_via_html(article_metadata, entry)
            return

        if response_data.get('status') != 200:
            logging.error("Reuters API returned status=%s for article %s", response_data.get('status'), article_id)
            self.__fetch_article_via_html(article_metadata, entry)
            return

        data = response_data.get('json')
        if not data:
            logging.error("Reuters article content response is empty for %s", article_id)
            self.__fetch_article_via_html(article_metadata, entry)
            return

        result = self.__extract_reuters_result(
            data=data,
            context=f"article content {article_id}",
            response=response_data,
            json_query=json_query,
            resource_link=request_link,
        )
        if result is None:
            self.__fetch_article_via_html(article_metadata, entry)
            return

        entry.description = ''
        entry.guid = article_metadata.guid
        entry.created_time = datetime.fromisoformat(article_metadata.created_time)

        if "related_content" in result:
            related_content = result["related_content"]
            if "images" in related_content:
                for image in related_content["images"]:
                    if "url" in image:
                        entry.description += "<figure>"
                        entry.description += f"<img src=\"{image['url']}\" alt=\"Image\">"
                        if "caption" in image:
                            entry.description += f"<figcaption>{image['caption']}</figcaption>"
                        entry.description += "</figure>"
            elif "galleries" in related_content:
                for gallery in related_content.get("galleries", []):
                    for element in gallery.get("content_elements", []):
                        if element.get("type") == "image" and "url" in element:
                            entry.description += "<figure>"
                            entry.description += f"<img src=\"{element['url']}\" alt=\"Image\">"
                            if "caption" in element:
                                entry.description += f"<figcaption>{element['caption']}</figcaption>"
                            entry.description += "</figure>"

        content = result.get('content_elements')
        if not isinstance(content, list):
            logging.warning(
                "Reuters article content payload missing content_elements list for %s link=%s",
                article_metadata.guid,
                article_metadata.link,
            )
            self.__fetch_article_via_html(article_metadata, entry)
            return

        for p in content:
            if isinstance(p, dict) and p.get("type") == "paragraph" and p.get("content"):
                entry.description += "<p>" + p["content"] + "</p>"

        if not entry.description:
            logging.warning(
                "Reuters built empty description for article id=%s link=%s",
                article_id, article_metadata.link,
            )
            self.__fetch_article_via_html(article_metadata, entry)
            return

        entry.persist_to_cache(self.router_path)

    def __fetch_article_via_html(self, article_metadata: Metadata, entry: FeedItem):
        logging.warning("Reuters falling back to HTML parsing for article %s", article_metadata.link)
        soup = get_link_content_with_bs_no_params(article_metadata.link, html_parser)
        body_candidates = [
            soup.find('article'),
            soup.find('section', {'data-testid': 'article-body'}),
            soup.find('div', class_=re.compile('ArticleBody|ArticleContent|article__body', re.IGNORECASE), recursive=True),
            soup.find('div', {'id': 'articleText'}),
            soup.find('div', role='main'),
        ]
        body = next((candidate for candidate in body_candidates if candidate), None)
        if body is None:
            logging.warning(
                "Reuters fallback HTML parser failed for %s, saving full page",
                article_metadata.link,
            )
            entry.description = soup.body or soup
        else:
            entry.description = body
        entry.persist_to_cache(self.router_path)

    def _generate_response(self, last_build_time, feed_entries_list, parameter=None):
        feed_title = "Reuters News - " + f"{parameter['category']} - {parameter['topic'] + '' if parameter['topic'] else ''}"
        feed_description = reuters_description
        feed_original_link = reuters_site_link
        feed = generate_feed_object_for_new_router(
            title=feed_title,
            link=feed_original_link,
            description=feed_description,
            language=language_english,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list,
        )
        return feed