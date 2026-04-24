import logging

from router.base_router import BaseRouter
from utils.feed_item_object import FeedItem, Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from router.earthquake.usgs_earthquake_router_constants import usgs_earthquake_name
from utils.get_link_content import load_json_response
from utils.time_converter import convert_millisecond_to_datetime_with_format, convert_millisecond_to_datetime


class UsgsEarthquakeRouter(BaseRouter):

    @staticmethod
    def _build_entry_from_feature(feature: dict) -> dict:
        """Parse a single GeoJSON feature into a flat payload dict.

        Single source of truth for all earthquake fields — called once per
        feature inside get_articles_list(), so the USGS API is only hit once
        per refresh cycle.
        """
        properties = feature["properties"]

        loc = f"<p>Location: {properties['place']}</p>"
        occurred_time = (
            f"<p>Time: {str(convert_millisecond_to_datetime_with_format(properties['time']))}</p>"
        )
        depth = f"<p>Depth: {str(feature['geometry']['coordinates'][2])} KM</p>"
        url = (
            f"<p>Details: <a href=\"{properties['url']}\">Click to see details...</a></p>"
        )

        return {
            "title": properties["title"],
            "link": properties["url"],
            "author": usgs_earthquake_name,
            "created_time": convert_millisecond_to_datetime(properties["time"]),
            "guid": properties["ids"],
            "description": loc + occurred_time + depth + url,
        }

    def get_articles_list(
            self, parameter=None, link_filter=None, title_filter=None
    ) -> list:
        """Fetch the USGS GeoJSON feed ONCE and build the Metadata list.

        The pre-built description is stored in Metadata.flag so that
        get_article_content() can reuse it without any additional network call.
        load_json_response() handles logging internally.
        """
        logging.info("Router %s fetching USGS GeoJSON feed from %s", self.router_path, self.articles_link)
        json_response = load_json_response(self.articles_link)
        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)

        metadata_list = []
        for feature in json_response["features"]:
            payload = self._build_entry_from_feature(feature)
            cache_key = generate_cache_key(
                cache_prefix, payload["guid"] or payload["link"]
            )
            metadata = Metadata(
                title=payload["title"],
                link=payload["link"],
                author=payload["author"],
                created_time=payload["created_time"],
                guid=payload["guid"],
                cache_key=cache_key,
                # Pre-built description stashed in flag — no second HTTP call needed.
                flag=payload["description"],
            )
            metadata_list.append(metadata)
        logging.info("Router %s built %d article metadata entries from USGS feed", self.router_path, len(metadata_list))
        return metadata_list

    def get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        """Populate entry from data already parsed in get_articles_list().

        No network call is made here. The USGS API is called exactly once
        per refresh cycle (inside get_articles_list()).
        """
        logging.debug("Router %s populating article from pre-built flag link=%s", self.router_path, article_metadata.link)
        entry.title = article_metadata.title
        entry.link = article_metadata.link
        entry.author = article_metadata.author
        entry.created_time = article_metadata.created_time
        entry.guid = article_metadata.guid
        entry.description = article_metadata.flag  # pre-built in get_articles_list()
        entry.persist_to_cache(self.router_path)
        logging.debug("Router %s persisted article to cache link=%s", self.router_path, article_metadata.link)
        return entry.description