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

        return metadata_list
