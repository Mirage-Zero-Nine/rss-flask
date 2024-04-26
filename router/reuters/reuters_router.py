import json
import logging
from datetime import datetime

import requests
from router.base_router import BaseRouter
from router.reuters.reuters_constants import reuters_articles_list_api_link, reuters_article_content_api_link, \
    reuters_site_link, reuters_description
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix, FeedItem
from utils.router_constants import language_english
from utils.time_converter import convert_time_with_pattern
from utils.xml_utilities import generate_feed_object_for_new_router


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
        response = requests.get(root_url + json_query)
        data = response.json()
        articles = data["result"]["articles"]

        for article in articles:
            save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
            metadata = Metadata(
                title=article["title"],
                created_time=convert_time_with_pattern(article["published_time"], "%Y-%m-%dT%H:%M:%S.%fZ").isoformat(),
                link=article["canonical_url"],
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
        response = requests.get(root_url + json_query)
        data = response.json()
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


if __name__ == '__main__':
    li = handler('world', '', 3)
    for l in li:
        handler1(FeedItem(description=''), l.link)
    # print(handler('world', '', 2))
    # print(handler1())
