import datetime as dt
import json
import logging
import os
import time
import pytz

from flask import make_response
from datetime import datetime

from data.feed_item_object import generate_json_name, convert_router_path_to_save_path_prefix, Metadata
from data.rss_cache import last_build_time_cache
from utils.xml_utilities import generate_feed_object_for_new_router


class BaseRouterNew:
    """
    Represents a feed information object.

    Args:
        router_path (str): The path to current router.
        feed_title (str): The title of the feed
        original_link (str): The link to the original site (not the link to each post).
        articles_link (str): The link to the page of getting articles (to get a list of articles)
        description (str): A description of the feed.
        language (str): The language used in the feed.
        feed_cache_key (str): The key used in cache to avoid duplicated feed. Needs to be unique.
        period (str): The refresh period.
    """

    def __init__(self, router_path, feed_title, original_link, articles_link, description, language, feed_cache_key,
                 period):
        self.router_path = router_path
        self.feed_title = feed_title
        self.original_link = original_link
        self.articles_link = articles_link
        self.description = description
        self.language = language
        self.feed_cache_key = feed_cache_key
        self.period = period

    def _get_articles_list(self, link_filter=None, title_filter=None):
        """
        Override this method for each router.
        :return: list of articles
        """
        return []

    def _get_individual_article(self, article_metadata):
        return []

    def get_rss_xml_response(self, parameter=None, link_filter=None, title_filter=None):
        """
        Entry point of the router.
        :return: XML feed
        """
        if parameter is None:
            cache_key = self.router_path
        else:
            cache_key = f"{self.router_path}/{parameter}"

        logging.info(f"Refreshing content: {self.router_path}")
        feed_entries_list = []

        save_path_prefix = convert_router_path_to_save_path_prefix(cache_key)
        # create a directory to save json
        os.makedirs(save_path_prefix, exist_ok=True)

        article_list_file_name = generate_json_name(save_path_prefix, self.feed_title)

        # get metadata of the articles
        if cache_key in last_build_time_cache.keys() and self.__check_if_meet_refresh_time(
                datetime.timestamp(last_build_time_cache[cache_key])) is False and os.path.exists(
                article_list_file_name):
            logging.info(f"Reading saved content for {cache_key}...")
            article_metadata_list = self.__read_article_list_from_file(article_list_file_name)
            last_build_time = last_build_time_cache[cache_key]
        else:
            logging.info(f"Query latest content for {cache_key}...")

            article_metadata_list = self._get_articles_list(link_filter, title_filter)
            self.__write_article_list_to_file(article_list_file_name, article_metadata_list)

            last_build_time = dt.datetime.now(pytz.timezone('GMT'))
            last_build_time_cache[cache_key] = last_build_time

        for article_metadata in article_metadata_list:
            feed_entries_list.append(self._get_individual_article(article_metadata))

        feed = generate_feed_object_for_new_router(
            title=self.feed_title,
            link=self.original_link,
            description=self.description,
            language=self.language,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list
        )

        logging.info(f"last build date: {feed.lastBuildDate}")

        response = make_response(feed.rss())
        response.headers.set('Content-Type', 'application/rss+xml')

        return response

    def __check_if_meet_refresh_time(self, last_query_time):
        logging.info("last query time: " + str(round(last_query_time) * 1000))
        logging.info("current time: " + str(round(time.time() * 1000)))
        logging.info("cooldown period: " + str(self.period))

        if round(time.time() * 1000) - round(last_query_time * 1000) > int(self.period):
            return True

        return False

    @staticmethod
    def __read_article_list_from_file(file_path):
        with open(file_path, 'r') as json_file:
            metadata_dicts = json.load(json_file)

        # Convert the dictionaries back to Metadata objects
        metadata_objects = []
        for metadata_dict in metadata_dicts:
            metadata_objects.append(Metadata(**metadata_dict))
        return metadata_objects

    @staticmethod
    def __write_article_list_to_file(file_name, article_metadata_list):
        metadata_dicts = []
        for metadata in article_metadata_list:
            metadata_dicts.append(metadata.__dict__)

        with open(file_name, 'w') as json_file:
            json.dump(metadata_dicts, json_file)
