import datetime as dt

import pytz

from router.base_router import BaseRouter
from router.earthquake.usgs_earthquake_router_constants import usgs_earthquake_name
from utils.cache_store import write_build_time
from utils.feed_item_object import (
    FeedItem,
    Metadata,
    convert_router_path_to_save_path_prefix,
    generate_json_name,
)
from utils.helpers import convert_millisecond_to_datetime, convert_millisecond_to_datetime_with_format
from utils.http_client import load_json_response


class UsgsEarthquakeRouter(BaseRouter):
    def refresh_cache(self, parameter=None, link_filter=None, title_filter=None):
        cache_key = self._generate_cache_key_for_router(parameter)
        self._log_info(f"refresh earthquake cache cache_key={cache_key}")
        json_response = load_json_response(self.articles_link)
        metadata_list = []
        content_count = 0

        for feature in json_response["features"]:
            guid = feature["properties"]["ids"]
            link = feature["properties"]["url"]
            article_cache_key = generate_json_name(
                convert_router_path_to_save_path_prefix(self.router_path),
                guid,
            )
            metadata_list.append(
                Metadata(
                    title=feature["properties"]["title"],
                    link=link,
                    guid=guid,
                    created_time=convert_millisecond_to_datetime(feature["properties"]["time"]).isoformat(),
                    json_name=article_cache_key,
                )
            )

            loc = "<p>Location: " + feature["properties"]["place"] + "</p>"
            occurred_time = "<p>Time: " + str(
                convert_millisecond_to_datetime_with_format(feature["properties"]["time"], 7)
            ) + "</p>"
            depth = "<p>Depth: " + str(feature["geometry"]["coordinates"][2]) + " KM</p>"
            url = '<p>Details: <a href="%s">Click to see details...</a> ' % link
            feed_item = FeedItem(
                title=feature["properties"]["title"],
                link=link,
                author=usgs_earthquake_name,
                created_time=convert_millisecond_to_datetime(feature["properties"]["time"]),
                guid=guid,
                description=loc + occurred_time + depth + url,
            )
            feed_item.save_to_cache(self.router_path)
            content_count += 1

        self._write_article_list_to_cache(self._build_article_list_key(cache_key), metadata_list)
        last_build_time = dt.datetime.now(pytz.timezone("GMT"))
        write_build_time(cache_key, last_build_time)
        self._log_info(
            f"refresh completed cache_key={cache_key} metadata_count={len(metadata_list)} "
            f"content_count={content_count} last_build_time={last_build_time.isoformat()}"
        )
        return {
            "cache_key": cache_key,
            "metadata_count": len(metadata_list),
            "content_count": content_count,
            "last_build_time": last_build_time,
        }
