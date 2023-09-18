import feedparser

from data.feed_item_object import FeedItem
from data.rss_cache import feed_item_cache
from router.base_router import BaseRouter
from utils.tools import check_need_to_filter


class RouterForRssFeed(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None):
        article_list = []
        parse_feed = feedparser.parse(self.original_link)
        for entry in parse_feed.entries:
            entry_title = entry.title
            entry_link = entry.link

            if entry_link and entry_title:
                if check_need_to_filter(entry_link, entry_title, link_filter, title_filter) is False:
                    if entry_link in feed_item_cache.keys():
                        feed_item = feed_item_cache[entry_link]
                    else:
                        feed_item = FeedItem(title=entry_title,
                                             link=entry_link,
                                             guid=entry_link,
                                             with_content=False)
                    article_list.append(feed_item)

        return article_list
