import json
import logging
import re
from datetime import datetime
from urllib.parse import urljoin

from router.base_router import BaseRouter
from router.reuters.reuters_constants import reuters_articles_list_api_link, reuters_article_content_api_link, \
    reuters_site_link, reuters_description, headers
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix, FeedItem
from utils.http_client import get_response, log_json_decode_error
from utils.router_constants import html_parser, language_english
from utils.time_converter import convert_time_with_pattern
from utils.xml_utilities import generate_feed_object_for_new_router
from utils.get_link_content import get_link_content_with_bs_no_params


class ReutersRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []
        category, topic, limit = parameter['category'], parameter['topic'], parameter['limit']

        logging.info(f"category: {category}, topic:{topic}, limit: {limit}")
        section_id = f"/{category}/{topic + '/' if topic else ''}"

        root_url = self.articles_link + reuters_articles_list_api_link
        params = {
            'offset': 0,
            'size': limit,
            'section_id': section_id,
            'website': 'reuters',
        }
        json_query = json.dumps(params)
        response = get_response(root_url + json_query, headers=headers)
        try:
            data = response.json()
        except ValueError as exc:
            log_json_decode_error(
                f"Failed to decode Reuters article list JSON ({json_query})",
                response,
                exc,
            )
            return metadata_list
        articles = data["result"]["articles"]


        for article in articles:
            try:
                created_time = convert_time_with_pattern(article["published_time"], "%Y-%m-%dT%H:%M:%S.%fZ").isoformat()
            except ValueError:
                try:
                    created_time = convert_time_with_pattern(article["published_time"], "%Y-%m-%dT%H:%M:%SZ").isoformat()
                except ValueError:
                    created_time = None
                    logging.error("Created time conversion failed: %s", article["published_time"])

            if created_time:
                canonical_url = article.get("canonical_url")
                if not canonical_url:
                    logging.warning("Skipping Reuters article %s because canonical_url is missing", article["id"])
                    continue
                full_link = urljoin(self.original_link, canonical_url)
                save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                metadata = Metadata(
                    title=article["title"],
                    created_time=created_time,
                    link=full_link,
                    guid=article["id"],
                    author=", ".join(author["name"] for author in article["authors"]) if article["authors"] else "Reuters",
                    json_name=generate_json_name(prefix=save_json_path_prefix, name=article["id"])
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
        response = get_response(root_url + json_query, headers=headers)
        try:
            data = response.json()
        except ValueError as exc:
            log_json_decode_error(
                f"Failed to decode Reuters article content JSON for {article_metadata.guid}",
                response,
                exc,
            )
            self.__fetch_article_via_html(article_metadata, entry)
            return
        entry.description = ''
        entry.guid = article_metadata.guid
        entry.created_time = datetime.fromisoformat(article_metadata.created_time)

        if "related_content" in data['result']:
            related_content = data['result']["related_content"]
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

        content = data['result']['content_elements']
        for p in content:
            if p["type"] == "paragraph":
                entry.description += "<p>" + p["content"] + "</p>"

        entry.save_to_json(self.router_path)

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
