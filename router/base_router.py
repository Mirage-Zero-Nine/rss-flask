import logging
import time
from datetime import datetime

from flask import make_response

from data.rss_cache import feed_cache
from utils.xml_utilities import generate_feed_object


class BaseRouter:
    """
    Represents a feed information object.

    Args:
        name (str): The name of the feed.
        feed_title (str): The title of the feed used in the output RSS object.
        original_link (str): The link to the original site (not the link to each post).
        description (str): A description of the feed.
        language (str): The language used in the feed.
        key (str): The key used in cache.
        period (str): The refresh period.

    Attributes:
        name (str): The name of the feed.
        title (str): The title of the feed
        original_link (str): The link to the original site (not the link to each post).
        website_link (str): The title of the feed used in the output RSS object.
        description (str): A description of the feed.
        language (str): The language used in the feed.
        key (str): The key used in cache.
        period (str): The refresh period.
    """

    def __init__(self, name, feed_title, original_link, website_link, description, language, key, period):
        self.name = name
        self.title = feed_title
        self.original_link = original_link
        self.website_link = website_link
        self.description = description
        self.language = language
        self.key = key
        self.period = period

    def _get_articles_list(self, link_filter=None, title_filter=None):
        """
        Override this method for each router.
        :return: list of articles
        """
        return []

    def _get_individual_article(self, entry_list):
        pass

    def __generate_feed_rss(self, link_filter=None, title_filter=None):
        entry_list = self._get_articles_list(link_filter, title_filter)
        self._get_individual_article(entry_list)
        feed = generate_feed_object(
            title=self.title,
            link=self.original_link,
            description=self.description,
            language=self.language,
            feed_item_list=entry_list
        )

        return feed

    def get_rss_xml_response(self, link_filter=None, title_filter=None):
        """
        Entry point of the router.
        :return: XML feed
        """

        should_query = self.__check_query()

        if should_query is True:
            feed = self.__generate_feed_rss(link_filter, title_filter)
            feed_cache[self.key] = feed
        else:
            feed = feed_cache[self.key]

        response = make_response(feed.rss())
        response.headers.set('Content-Type', 'application/rss+xml')

        return response

    def __check_query(self):
        """
        Check if current router needs to refresh. Unit of period is minute.
        :return: if the app need to refresh the content for this router
        """
        should_refresh = (
                len(feed_cache) == 0
                or self.key not in feed_cache.keys()
                or self.__check_if_meet_refresh_time(datetime.timestamp(feed_cache[self.key].lastBuildDate))
        )
        logging.info(f"Query {self.name} for this call: {should_refresh}")

        return should_refresh

    def __check_if_meet_refresh_time(self, last_query_time):
        logging.info("last query time: " + str(round(last_query_time) * 1000))
        logging.info("current time: " + str(round(time.time() * 1000)))
        logging.info("cooldown period: " + str(self.period))

        if round(time.time() * 1000) - round(last_query_time * 1000) > int(self.period):
            return True

        return False
