import json
import logging
import re
from datetime import datetime
from urllib.parse import quote, urljoin

import requests
from router.base_router import BaseRouter
from router.reuters.reuters_constants import reuters_articles_list_api_link, reuters_article_content_api_link, \
    reuters_site_link, reuters_description, headers
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix, FeedItem
from utils.router_constants import html_parser, language_english
from utils.time_converter import convert_time_with_pattern
from utils.xml_utilities import generate_feed_object_for_new_router
from utils.get_link_content import get_link_content_with_bs_no_params


class ReutersRouter(BaseRouter):
    @staticmethod
    def __is_captcha_challenge(data):
        return isinstance(data, dict) and "url" in data and "captcha" in str(data.get("url", "")).lower()

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []
        category, topic, limit = parameter['category'], parameter['topic'], parameter['limit']

        logging.info(f"category: {category}, topic:{topic}, limit: {limit}")
        section_id = f"/{category}/{topic + '/' if topic else ''}"

        root_url = self.articles_link + reuters_articles_list_api_link
        section_link = self.__build_section_link(category=category, topic=topic)
        params = {
            'offset': 0,
            'size': limit,
            'section_id': section_id,
            'website': 'reuters',
        }
        json_query = json.dumps(params)
        request_link = self.__build_api_request_link(root_url, json_query)
        session = self.__create_reuters_session()
        self.__warm_session(session=session, warmup_link=section_link, context=f"section {section_link}")
        response = session.get(request_link)
        try:
            data = response.json()
        except ValueError as exc:
            snippet = response.text.replace('\n', ' ')[:200]
            logging.error(
                "Failed to decode Reuters article list JSON (%s). warmup_link=%s status=%s url=%s. Error: %s. Payload snippet: %s",
                json_query,
                section_link,
                response.status_code,
                response.url,
                exc,
                snippet
            )
            return metadata_list
        result = self.__extract_reuters_result(
            data=data,
            context="article list",
            response=response,
            json_query=json_query,
            resource_link=request_link
        )
        if result is None:
            return metadata_list

        articles = result.get("articles")
        if not isinstance(articles, list):
            logging.warning(
                "Reuters article list payload missing articles array. request_link=%s response_url=%s query=%s top_level_keys=%s result_keys=%s",
                request_link,
                response.url,
                json_query,
                sorted(data.keys()) if isinstance(data, dict) else type(data).__name__,
                sorted(result.keys()) if isinstance(result, dict) else type(result).__name__
            )
            return metadata_list


        for article in articles:
            if not isinstance(article, dict):
                logging.warning("Skipping Reuters article with unexpected type: %s", type(article).__name__)
                continue
            try:
                created_time = convert_time_with_pattern(article["published_time"], "%Y-%m-%dT%H:%M:%S.%fZ").isoformat()
            except ValueError:
                try:
                    created_time = convert_time_with_pattern(article["published_time"], "%Y-%m-%dT%H:%M:%SZ").isoformat()
                except ValueError:
                    created_time = None
                    logging.error(
                        "Creat time converting failure for article id=%s link=%s published_time=%s",
                        article.get("id", "<unknown>"),
                        article.get("canonical_url", "<missing>"),
                        article.get("published_time")
                    )
            except KeyError:
                created_time = None
                logging.warning(
                    "Skipping Reuters article without published_time: id=%s link=%s",
                    article.get("id", "<unknown>"),
                    article.get("canonical_url", "<missing>")
                )

            if created_time:
                canonical_url = article.get("canonical_url")
                if not canonical_url:
                    logging.warning("Skipping Reuters article %s because canonical_url is missing", article.get("id", "<unknown>"))
                    continue
                full_link = urljoin(self.original_link, canonical_url)
                save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                authors = article.get("authors") or []
                metadata = Metadata(
                    title=article.get("title", "Reuters"),
                    created_time=created_time,
                    link=full_link,
                    guid=article.get("id", full_link),
                    author=", ".join(author["name"] for author in authors if isinstance(author, dict) and author.get("name")) if authors else "Reuters",
                    json_name=generate_json_name(prefix=save_json_path_prefix, name=article.get("id", full_link))
                )
                metadata_list.append(metadata)

        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        root_url = self.articles_link + reuters_article_content_api_link
        params = {
            'id': article_metadata.guid,
            'website': 'reuters',
        }
        json_query = json.dumps(params)
        request_link = self.__build_api_request_link(root_url, json_query)
        session = self.__create_reuters_session()
        self.__warm_session(session=session, warmup_link=article_metadata.link, context=f"article {article_metadata.link}")
        response = session.get(request_link)
        try:
            data = response.json()
        except ValueError as exc:
            snippet = response.text.replace('\n', ' ')[:200]
            logging.error(
                "Failed to decode Reuters article content JSON for %s link=%s request_link=%s (status=%s url=%s). Error: %s. Payload snippet: %s",
                article_metadata.guid,
                article_metadata.link,
                request_link,
                response.status_code,
                response.url,
                exc,
                snippet
            )
            self.__fetch_article_via_html(article_metadata, entry)
            return
        result = self.__extract_reuters_result(
            data=data,
            context=f"article content {article_metadata.guid}",
            response=response,
            json_query=json_query,
            resource_link=request_link
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
                images = related_content["images"]
                for image in images:
                    if "url" in image:
                        entry.description += "<figure>"
                        entry.description += f"<img src=\"{image['url']}\" alt=\"Image\">"
                        if "caption" in image:
                            entry.description += f"<figcaption>{image['caption']}</figcaption>"
                        entry.description += "</figure>"
            elif "galleries" in related_content:
                galleries = related_content["galleries"]
                for gallery in galleries:
                    if "content_elements" in gallery:
                        content_elements = gallery["content_elements"]
                        for element in content_elements:
                            if element["type"] == "image" and "url" in element:
                                entry.description += "<figure>"
                                entry.description += f"<img src=\"{element['url']}\" alt=\"Image\">"
                                if "caption" in element:
                                    entry.description += f"<figcaption>{element['caption']}</figcaption>"
                                entry.description += "</figure>"

        content = result.get('content_elements')
        if not isinstance(content, list):
            logging.warning(
                "Reuters article content payload missing content_elements list for %s link=%s request_link=%s. url=%s query=%s",
                article_metadata.guid,
                article_metadata.link,
                request_link,
                response.url,
                json_query
            )
            self.__fetch_article_via_html(article_metadata, entry)
            return
        for p in content:
            if isinstance(p, dict) and p.get("type") == "paragraph" and p.get("content"):
                entry.description += "<p>" + p["content"] + "</p>"

        entry.save_to_json(self.router_path)

    @staticmethod
    def __build_api_request_link(root_url, json_query):
        return root_url + quote(json_query, safe="")

    def __build_section_link(self, category, topic=None):
        path = f"/{category}/"
        if topic:
            path += f"{topic}/"
        return urljoin(self.original_link, path)

    @staticmethod
    def __create_reuters_session():
        session = requests.Session()
        session.headers.update(headers)
        return session

    @staticmethod
    def __warm_session(session, warmup_link, context):
        try:
            response = session.get(warmup_link)
            logging.info(
                "Reuters warmup request for %s returned status=%s url=%s cookies=%s",
                context,
                response.status_code,
                response.url,
                list(session.cookies.keys())
            )
        except requests.RequestException as exc:
            logging.warning("Reuters warmup request failed for %s: %s", context, exc)

    @staticmethod
    def __extract_reuters_result(data, context, response, json_query, resource_link=None):
        if not isinstance(data, dict):
            logging.error(
                "Unexpected Reuters %s payload type. resource_link=%s status=%s url=%s query=%s payload_type=%s",
                context,
                resource_link,
                response.status_code,
                response.url,
                json_query,
                type(data).__name__
            )
            return None

        if ReutersRouter.__is_captcha_challenge(data):
            logging.error(
                "Reuters %s blocked by captcha. resource_link=%s status=%s url=%s query=%s challenge_url=%s",
                context,
                resource_link,
                response.status_code,
                response.url,
                json_query,
                data.get("url")
            )
            return None

        result = data.get("result")
        if isinstance(result, dict):
            return result

        logging.error(
            "Reuters %s payload missing result object. resource_link=%s status=%s url=%s query=%s top_level_keys=%s payload_snippet=%s",
            context,
            resource_link,
            response.status_code,
            response.url,
            json_query,
            sorted(data.keys()),
            response.text.replace('\n', ' ')[:200]
        )
        return None

    def __fetch_article_via_html(self, article_metadata: Metadata, entry: FeedItem):
        soup = get_link_content_with_bs_no_params(article_metadata.link, html_parser)
        body_candidates = [
            soup.find('article'),
            soup.find('section', {'data-testid': 'article-body'}),
            soup.find('div', class_=re.compile('ArticleBody|ArticleContent|article__body'), recursive=True),
            soup.find('div', {'id': 'articleText'}),
            soup.find('div', role='main')
        ]
        body = next((candidate for candidate in body_candidates if candidate), None)
        if body is None:
            logging.warning("Reuters fallback HTML parser failed for %s, saving full page", article_metadata.link)
            entry.description = soup.body or soup
        else:
            entry.description = body
        entry.save_to_json(self.router_path)

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
            feed_item_list=feed_entries_list
        )

        return feed
