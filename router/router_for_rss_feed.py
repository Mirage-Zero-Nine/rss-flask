import feedparser

from data.feed_item_object import Metadata, convert_router_path_to_save_path_prefix, generate_json_name
from router.base_router_new import BaseRouterNew
from utils.tools import check_need_to_filter


class RouterForRssFeed(BaseRouterNew):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        metadata_list = []
        parse_feed = feedparser.parse(self.articles_link)
        for entry in parse_feed.entries:
            entry_title = entry.title
            entry_link = entry.link
            save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
            if entry_link and entry_title:
                if check_need_to_filter(entry_link, entry_title, link_filter, title_filter) is False:
                    feed_item = Metadata(title=entry_title,
                                         link=entry_link,
                                         json_name=generate_json_name(prefix=save_json_path_prefix, name=entry_link))
                    metadata_list.append(feed_item)

        return metadata_list
