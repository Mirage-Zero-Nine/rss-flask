import feedparser

from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix
from utils.helpers import check_need_to_filter
from router.base_router import BaseRouter


class RouterForRssFeed(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        metadata_list = []
        self._log_info(f"fetch rss source url={self.articles_link}")
        parse_feed = feedparser.parse(self.articles_link)
        for entry in parse_feed.entries:
            entry_title = entry.title
            entry_link = entry.link
            entry_create_time = entry.published
            if entry_link and entry_title:
                save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                if check_need_to_filter(entry_link, entry_title, link_filter, title_filter) is False:
                    feed_item = Metadata(title=entry_title,
                                         link=entry_link,
                                         created_time=entry_create_time,
                                         json_name=generate_json_name(prefix=save_json_path_prefix, name=entry_link))
                    metadata_list.append(feed_item)

        return metadata_list
