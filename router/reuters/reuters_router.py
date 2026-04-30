import json
import logging
import re
from urllib.parse import quote
from datetime import datetime

import requests
from router.base_router import BaseRouter
from router.reuters.reuters_constants import (
    reuters_articles_list_api_link,
    reuters_article_content_api_link,
    reuters_site_link,
    reuters_description,
    headers,
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
        """Fetch URL via plain requests and return structured result."""
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            status = response.status_code
            try:
                json_data = response.json()
            except ValueError:
                json_data = None
            return {
                'status': status,
                'json': json_data,
                'error': None,
                'url': response.url,
                'text': response.text,
            }
        except requests.RequestException as e:
            logging.warning("Request error for %s: %s", url, e)
            return {
                'status': None,
                'json': None,
                'error': str(e),
                'url': url,
                'text': '',
            }

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
                response.get('url'),
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
            "Reuters %s payload missing result object. resource_link=%s status=%s url=%s query=%s top_level_keys=%s payload_snippet=%s",
            context,
            resource_link,
            response.get('status'),
            response.get('url'),
            json_query,
            sorted(data.keys()),
            (response.get('text') or '').replace('\n', ' ')[:200],
        )
        return None

    @staticmethod
    def __build_api_request_link(root_url, json_query):
        return root_url + quote(json_query, safe="")

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []
        category, topic, limit = parameter['category'], parameter['topic'], parameter['limit']

        logging.info("Reuters list request category=%s topic=%s limit=%s", category, topic, limit)
        section_id = f"/{category}/{topic + '/' if topic else ''}"
        root_url = self.articles_link + reuters_articles_list_api_link

        json_query = json.dumps({
            'offset': 0,
            'size': limit,
            'section_id': section_id,
            'website': 'reuters',
        })
        request_link = self.__build_api_request_link(root_url, json_query)

        log_external_fetch(
            "requests",
            request_link,
            resource="reuters_articles_list",
        )
        response_data = self._fetch_with_requests(request_link)

        if response_data.get('error'):
            logging.error(
                "Request error fetching Reuters articles list category=%s topic=%s request_link=%s: %s",
                category,
                topic,
                request_link,
                response_data['error'],
            )
            return []

        if response_data.get('status') != 200:
            logging.error(
                "Reuters API returned status=%s for articles list category=%s topic=%s request_link=%s response_url=%s",
                response_data.get('status'),
                category,
                topic,
                request_link,
                response_data.get('url'),
            )
            return []

        data = response_data.get('json')
        if not data:
            logging.error(
                "Reuters articles list response is empty category=%s topic=%s request_link=%s response_url=%s snippet=%s",
                category,
                topic,
                request_link,
                response_data.get('url'),
                (response_data.get('text') or '').replace('\n', ' ')[:200],
            )
            return []

        result = self.__extract_reuters_result(
            data=data,
            context="articles list",
            response=response_data,
            json_query=json_query,
            resource_link=request_link,
        )
        if result is None:
            logging.error(
                "Reuters articles list extract failed category=%s topic=%s request_link=%s",
                category,
                topic,
                request_link,
            )
            return []

        articles = result.get("articles", [])
        for article in articles:
            if not article.get("title"):
                continue
            if not article.get("canonical_url"):
                continue
            if link_filter and link_filter not in article.get("canonical_url", ""):
                continue
            if title_filter and title_filter in article.get("title", ""):
                continue
            canonical_url = article.get("canonical_url")
            full_link = "https://www.reuters.com" + canonical_url
            cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
            cache_key = generate_cache_key(prefix=cache_prefix, name=article.get("id", ""))
            created_time = self.__resolve_created_time(article, cache_key)

            metadata_list.append(Metadata(
                title=article.get('title', ''),
                link=full_link,
                guid=article.get("id", ""),
                created_time=created_time,
                cache_key=cache_key,
            ))

        logging.info("Reuters built %d metadata entries for category=%s topic=%s", len(metadata_list), category, topic)
        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        article_id = article_metadata.guid
        root_url = self.articles_link + reuters_article_content_api_link
        json_query = json.dumps({
            'id': article_id,
            'website': 'reuters',
        })
        request_link = self.__build_api_request_link(root_url, json_query)

        log_external_fetch(
            "requests",
            request_link,
            resource="reuters_article_content",
            article_link=article_metadata.link,
        )
        response_data = self._fetch_with_requests(request_link)

        if response_data.get('error'):
            logging.error(
                "Request error fetching Reuters article content article_id=%s link=%s request_link=%s: %s",
                article_id,
                article_metadata.link,
                request_link,
                response_data['error'],
            )
            self.__fetch_article_via_html(article_metadata, entry)
            return

        if response_data.get('status') != 200:
            logging.error(
                "Reuters API returned status=%s for article_id=%s link=%s request_link=%s response_url=%s",
                response_data.get('status'),
                article_id,
                article_metadata.link,
                request_link,
                response_data.get('url'),
            )
            self.__fetch_article_via_html(article_metadata, entry)
            return

        data = response_data.get('json')
        if not data:
            logging.error(
                "Reuters article content response is empty for article_id=%s link=%s request_link=%s response_url=%s snippet=%s",
                article_id,
                article_metadata.link,
                request_link,
                response_data.get('url'),
                (response_data.get('text') or '').replace('\n', ' ')[:200],
            )
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
                "Reuters article content payload missing content_elements list for %s link=%s request_link=%s response_url=%s",
                article_metadata.guid,
                article_metadata.link,
                request_link,
                response_data.get('url'),
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
        body_text = soup.get_text(" ", strip=True)[:200].lower()
        if "enable javascript" in body_text or "please enable js" in body_text or "captcha" in body_text:
            logging.warning(
                "Reuters HTML fallback likely returned bot-challenge content for %s snippet=%s; skipping cache write",
                article_metadata.link,
                body_text,
            )
            entry.description = None
            return

        logging.info("Reuters HTML fallback used successfully for %s", article_metadata.link)
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
