import logging
import feedparser

from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.log_context import log_external_fetch
from router.base_router import BaseRouter
from utils.tools import check_need_to_filter


class RouterForRssFeed(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        metadata_list = []
        log_external_fetch("feedparser.parse", self.articles_link)
        parse_feed = feedparser.parse(self.articles_link)
        if not parse_feed.entries:
            bozo = parse_feed.get('bozo', False)
            bozo_exception = parse_feed.get('bozo_exception')
            logging.warning(
                "Router %s RSS feed has 0 entries (bozo=%s, feed_url=%s, bozo_exception=%s)",
                self.router_path, bozo, self.articles_link, bozo_exception,
            )
        for entry in parse_feed.entries:
            entry_title = entry.title
            entry_link = entry.link
            entry_create_time = entry.published
            if entry_link and entry_title:
                cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
                if check_need_to_filter(entry_link, entry_title, link_filter, title_filter) is False:
                    feed_item = Metadata(title=entry_title,
                                         link=entry_link,
                                         created_time=entry_create_time,
                                         cache_key=generate_cache_key(prefix=cache_prefix, name=entry_link))
                    metadata_list.append(feed_item)

        if not metadata_list:
            logging.warning(
                "Router %s built 0 metadata entries from RSS feed %s (total entries=%d)",
                self.router_path, self.articles_link, len(parse_feed.entries),
            )
        return metadata_list
