import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from utils.cache_store import write_feed_item_to_cache


@dataclass
class FeedItem:
    """
    RSS feed item payload stored in Redis.

    description can be a BeautifulSoup/Tag object while routers are building content;
    persist_to_cache normalizes it to a string for Redis.
    """

    title: str | None = None
    link: str | None = None
    description: Any | None = None
    author: str | None = None
    guid: str | None = None
    created_time: datetime | str | int | float | None = None
    with_content: bool = False
    cache_key: str = field(default="")

    def __repr__(self):
        # Handle None values by providing default values or converting to empty string
        title = self.title or ""
        link = self.link or ""
        author = self.author or ""
        created_time = str(self.created_time) if self.created_time else ""
        description = str(self.description) if self.description else ""
        guid = self.guid or ""
        with_content = str(self.with_content)

        return "title: " + title + '\n' + \
            "link: " + link + '\n' + \
            "author: " + author + '\n' + \
            "created_time: " + created_time + '\n' + \
            "description: " + description + '\n' + \
            "guid: " + guid + '\n' + \
            "with content? " + with_content

    def persist_to_cache(self, router_path: str, cache_key_override: str | None = None) -> None:
        """
        Store the feed item in Redis under the router-specific cache prefix.
        :param router_path: name of the router path
        :param cache_key_override: exact Redis key to use for shared-cache writes
        """
        cache_prefix = convert_router_path_to_cache_prefix(router_path)
        identifier = self.guid or self.link or self.title or datetime.now(timezone.utc).isoformat()
        self.cache_key = cache_key_override or generate_cache_key(cache_prefix, identifier)
        payload = {
            "title": self.title,
            "link": self.link,
            "description": str(self.description) if self.description is not None else None,
            "author": self.author,
            "created_time": str(self.created_time) if self.created_time else None,
            "guid": self.guid,
            "with_content": self.with_content
        }
        write_feed_item_to_cache(self.cache_key, payload)


@dataclass
class Metadata:
    """
    Lightweight article metadata snapshot stored separately from article content.
    """

    title: str = ""
    link: str = ""
    author: str | None = None
    guid: str = ""
    created_time: datetime | str | int | float | None = None
    cache_key: str = ""
    flag: Any | None = None


def generate_cache_key(prefix: str, name: str) -> str:
    encoded_name = base64.urlsafe_b64encode(name.encode('utf-8')).decode('utf-8').rstrip('=')
    if len(encoded_name) > 100:
        encoded_name = encoded_name[-100:]
    return f"{prefix}:{encoded_name}"


def convert_router_path_to_cache_prefix(router_path: str) -> str:
    if router_path.startswith('/') is False:
        logging.error(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Invalid path, it's not started with a '/': {router_path}")
        raise Exception("Invalid path, it's not started with a '/'")

    sanitized = router_path[1:].replace('/', '-')
    return f"router_cache:{sanitized}"
