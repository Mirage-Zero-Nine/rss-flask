import logging

import requests

from router.base_router import BaseRouter
from router.earthquake.usgs_earthquake_router_constants import usgs_earthquake_name
from utils.feed_item_object import FeedItem, Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.time_converter import convert_millisecond_to_datetime_with_format, convert_millisecond_to_datetime


class UsgsEarthquakeRouter(BaseRouter):


    def _build_entry_from_feature(self, feature: dict) -> dict | None:
        """Parse a single GeoJSON feature into a flat payload dict.

        Single source of truth for all earthquake fields — called once per
        feature inside get_articles_list(), so the USGS API is only hit once
        per refresh cycle.
        """
        properties = feature["properties"]

        place = properties.get("place") or "Unknown location"
        loc = f"<p>Location: {place}</p>"
        time_val = properties.get("time")
        occurred_time = (
            f"<p>Time: {str(convert_millisecond_to_datetime_with_format(time_val))}</p>"
            if time_val else "<p>Time: Unknown</p>"
        )
        coords = feature["geometry"]["coordinates"]
        depth_val = coords[2] if coords and len(coords) > 2 else None
        depth = f"<p>Depth: {str(depth_val) if depth_val else 'Unknown'} KM</p>"
        url_val = properties.get("url") or ""
        url = (
            f'<p>Details: <a href="{url_val}">Click to see details...</a></p>'
            if url_val else "<p>Details: N/A</p>"
        )

        title = properties.get("title") or ""
        link = properties.get("url") or ""
        if not title:
            logging.warning(
                "Router %s GeoJSON feature has no title, skipping ids=%s",
                self.router_path,
                properties.get("ids"),
            )
            return None
        if not link:
            logging.warning(
                "Router %s GeoJSON feature has no url, skipping ids=%s",
                self.router_path,
                properties.get("ids"),
            )
            return None

        return {
            "title": title,
            "link": link,
            "author": usgs_earthquake_name,
            "created_time": convert_millisecond_to_datetime(time_val) if time_val else None,
            "guid": properties.get("ids", {}).get("ce", link),
            "description": loc + occurred_time + depth + url,
        }

    def _get_articles_list(
            self, parameter=None, link_filter=None, title_filter=None
    ) -> list:
        """Fetch the USGS GeoJSON feed ONCE and build the Metadata list.

        The pre-built description is stored in Metadata.flag so that
        get_article_content() can reuse it without any additional network call.
        load_json_response() handles logging internally.
        """
        logging.info("Router %s fetching USGS GeoJSON feed from %s", self.router_path, self.articles_link)
        try:
            raw_response = requests.get(self.articles_link, timeout=30)
            logging.info(
                "Router %s USGS API response: status=%d content_length=%d",
                self.router_path,
                raw_response.status_code,
                len(raw_response.content),
            )
            if raw_response.status_code != 200:
                logging.warning(
                    "Router %s USGS API returned non-200 status=%d, body preview: %s",
                    self.router_path,
                    raw_response.status_code,
                    raw_response.text[:500],
                )
                return []
            json_response = raw_response.json()
        except requests.RequestException as e:
            logging.error("Router %s USGS API request failed: %s", self.router_path, e)
            return []
        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)

        metadata_list = []
        for feature in json_response["features"]:
            payload = self._build_entry_from_feature(feature)
            if payload is None:
                continue
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
        if not metadata_list:
            logging.warning(
                "Router %s USGS API returned 0 features, response keys=%s",
                self.router_path,
                sorted(json_response.keys()) if isinstance(json_response, dict) else type(json_response).__name__,
            )
        logging.info("Router %s built %d article metadata entries from USGS feed", self.router_path, len(metadata_list))
        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
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
