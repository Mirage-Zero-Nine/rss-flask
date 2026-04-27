import datetime as dt
import logging
import pytz

from flask import make_response
from datetime import datetime

from utils.cache_store import read_feed_item_from_cache, read_last_build_time, read_metadata_list, write_last_build_time, write_metadata_list
from utils.feed_item_object import Metadata, FeedItem, generate_cache_key, convert_router_path_to_cache_prefix
from utils.log_context import reset_current_router, set_current_router
from utils.xml_utilities import generate_feed_object_for_new_router


class BaseRouter:
    """
    Represents a feed information object.

    Args:
        router_path (str): The url path to current router that is access by RSS client.
        feed_title (str): The title of the feed.
        original_link (str): The link to the original site (not the link to each post).
        articles_link (str): The link to the page of getting articles (to get a list of articles).
        description (str): A description of the feed.
        language (str): The language used in the feed.
        period (int): The refresh period in milliseconds, default value is 600000 (10 minutes).
    """

    def __init__(self, router_path="", feed_title="", original_link="", articles_link="", description="", language="",
                 period=600000):
        self.router_path = router_path
        self.feed_title = feed_title
        self.original_link = original_link
        self.articles_link = articles_link
        self.description = description
        self.language = language
        self.period = period

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        """
        Override this method for each router.
        :return: list of articles
        """
        return []

    def _get_article(self, article_metadata):
        """
        Entry point to get content of each article.
        It will try to read if it's stored in Redis first, then do the actual query.
        Do not override this method in child router unless to modify the cache retrieval logic.
        Override _get_article_content instead.
        :param article_metadata: metadata of articles
        :return: entry that contains all the metadata and the content
        """
        cached_entry = self.__load_article_from_cache(article_metadata.cache_key)
        if cached_entry:
            logging.info("Router %s using cached article link=%s cache_key=%s", self.router_path, article_metadata.link, article_metadata.cache_key)
            if self.router_path == '/zaobao/realtime':
                description = cached_entry.description or ""
                logging.info("Zaobao cached article loaded for %s (content length=%s)", article_metadata.link, len(description))
                logging.debug("Zaobao cached article preview for %s: %s", article_metadata.link, description[:500])
                logging.debug("Zaobao cached article full content for %s: %s", article_metadata.link, description)
            return cached_entry

        logging.debug("Router %s retrieving article content link=%s", self.router_path, article_metadata.link)
        entry = FeedItem(title=article_metadata.title,
                         link=article_metadata.link,
                         guid=article_metadata.link)
        token = set_current_router(self.router_path)
        try:
            self._get_article_content(article_metadata, entry)
            if not entry.description:
                logging.warning("Router %s _get_article_content returned empty description for link=%s", self.router_path, article_metadata.link)
        except Exception as exc:
            logging.error("Router %s error during _get_article_content for link=%s: %s", self.router_path, article_metadata.link, exc)
        finally:
            reset_current_router(token)
        if not entry.description:
            logging.warning("Router %s returning article with empty description link=%s", self.router_path, article_metadata.link)
        return entry

    def _get_article_content(self, article_metadata, entry):
        """
        Actual method to retrieve content
        :param article_metadata: metadata of article
        :param entry: object stores all the metadata and the content
        """
        pass

    def get_rss_xml_response(self, parameter=None, link_filter=None, title_filter=None):
        """
        Read-only entry point of the router.
        :return: XML feed
        """
        logging.info("Router %s reading cached content parameter=%s", self.router_path, parameter)
        last_build_time, article_metadata_list = self._read_cached_article_metadata_list(parameter=parameter)
        if not article_metadata_list:
            logging.warning("Router %s no metadata in cache for parameter=%s; feed will be empty", self.router_path, parameter)
        feed_entries_list = self._build_feed_entries_from_metadata(article_metadata_list)
        if not feed_entries_list:
            logging.warning("Router %s built 0 feed entries for parameter=%s; serving empty feed", self.router_path, parameter)
        feed_last_build_time = last_build_time or dt.datetime.now(pytz.timezone('GMT'))
        feed = self._generate_response(last_build_time=feed_last_build_time,
                                       feed_entries_list=feed_entries_list,
                                       parameter=parameter)
        logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Last build date: {feed.lastBuildDate}")

        response = make_response(feed.rss())
        response.headers.set('Content-Type', 'application/rss+xml')
        return response

    def refresh_cache(self, parameter=None, link_filter=None, title_filter=None, force=False):
        logging.info("Router %s refreshing cache parameter=%s force=%s", self.router_path, parameter, force)
        cache_key = self.__generate_cache_key_for_router(parameter)
        logging.debug("Router %s cache key=%s", self.router_path, cache_key)
        last_build_time = read_last_build_time(cache_key)
        cached_metadata = self._read_cached_metadata_dicts(parameter=parameter)
        if force is False and last_build_time and self.__check_if_meet_refresh_time(datetime.timestamp(last_build_time)) is False and cached_metadata:
            logging.info("Router %s cache still fresh for cache_key=%s, skipping refresh", self.router_path, cache_key)
            return False

        logging.debug("Router %s retrieving article list source=%s cache_key=%s", self.router_path, self.articles_link, cache_key)
        token = set_current_router(self.router_path)
        try:
            article_metadata_list = self._get_articles_list(parameter=parameter,
                                                            link_filter=link_filter,
                                                            title_filter=title_filter)
            logging.info("Router %s fetched %d articles from source", self.router_path, len(article_metadata_list))
        except Exception as exc:
            logging.error("Router %s error during _get_articles_list: %s", self.router_path, exc)
            article_metadata_list = []
        finally:
            reset_current_router(token)
        article_list_key = self._build_article_list_cache_key(cache_key)
        self.__write_article_list_to_cache(article_list_key, article_metadata_list)

        for article_metadata in article_metadata_list:
            try:
                self._get_article(article_metadata)
            except Exception as exc:
                logging.exception("Router %s failed to retrieve article content link=%s cache_key=%s: %s",
                                  self.router_path, article_metadata.link, article_metadata.cache_key, exc)

        last_build_time = dt.datetime.now(pytz.timezone('GMT'))
        write_last_build_time(cache_key, last_build_time)
        return True

    def warm_cache(self, parameter=None, link_filter=None, title_filter=None):
        last_build_time, article_metadata_list = self._read_cached_article_metadata_list(parameter=parameter)
        if article_metadata_list and last_build_time:
            logging.info("Router %s cache warm-up skipped; Redis already populated for parameter=%s", self.router_path, parameter)
            return False

        if not article_metadata_list:
            logging.warning("Router %s warm-up proceeding; no existing metadata in cache for parameter=%s", self.router_path, parameter)
        logging.info("Router %s cache warm-up started for parameter=%s", self.router_path, parameter)
        return self.refresh_cache(parameter=parameter, link_filter=link_filter, title_filter=title_filter, force=True)

    def _generate_response(self, last_build_time, feed_entries_list, parameter):

        return generate_feed_object_for_new_router(
            title=self.feed_title,
            link=self.original_link,
            description=self.description,
            language=self.language,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list
        )

    def _read_cached_article_metadata_list(self, parameter=None):
        cache_key = self.__generate_cache_key_for_router(parameter)
        article_list_key = self._build_article_list_cache_key(cache_key)
        cached_metadata = read_metadata_list(article_list_key)
        if not cached_metadata:
            logging.debug("Router %s cache miss: no metadata list for key=%s", self.router_path, article_list_key)
        else:
            logging.debug("Router %s cache hit: %d metadata dicts for key=%s", self.router_path, len(cached_metadata), article_list_key)
        last_build_time = read_last_build_time(cache_key)
        article_metadata_list = self.__build_metadata_list(cached_metadata)
        if not article_metadata_list and cached_metadata:
            logging.warning("Router %s __build_metadata_list returned empty list from %d cached dicts for key=%s", self.router_path, len(cached_metadata), article_list_key)
        return last_build_time, article_metadata_list

    def _read_cached_metadata_dicts(self, parameter=None):
        cache_key = self.__generate_cache_key_for_router(parameter)
        article_list_key = self._build_article_list_cache_key(cache_key)
        return read_metadata_list(article_list_key)

    def _build_article_list_cache_key(self, router_cache_key):
        cache_prefix = convert_router_path_to_cache_prefix(router_cache_key)
        return generate_cache_key(cache_prefix, self.feed_title)

    def _build_feed_entries_from_metadata(self, article_metadata_list):
        feed_entries_list = []
        for article_metadata in article_metadata_list:
            entry = self.__load_article_from_cache(article_metadata.cache_key)
            if entry is None:
                logging.debug("Router %s cache miss for article key=%s (link=%s)", self.router_path, article_metadata.cache_key, article_metadata.link)
            if entry is not None and entry.description is not None:
                feed_entries_list.append(entry)
            elif entry is not None:
                logging.debug("Router %s article key=%s (link=%s) dropped: description is None", self.router_path, article_metadata.cache_key, article_metadata.link)
        logging.info("Router %s built %d feed entries from cache", self.router_path, len(feed_entries_list))
        if len(feed_entries_list) < len(article_metadata_list):
            logging.info("Router %s dropped %d entries (missing description) out of %d metadata items", self.router_path, len(article_metadata_list) - len(feed_entries_list), len(article_metadata_list))
        return feed_entries_list

    def __generate_cache_key_for_router(self, parameter=None):
        logging.debug("Router %s generating cache key parameter=%s", self.router_path, parameter)
        if parameter is None:
            cache_key = self.router_path
        else:
            values = [str(value) for value in parameter.values()]

            # Combine values into a string
            combined_values = "/".join(values)
            cache_key = f"{self.router_path}/{combined_values}"
        return cache_key

    def __check_if_meet_refresh_time(self, last_query_time):
        logging.debug("Router %s last_query_time_ms=%s cooldown_period_ms=%s", self.router_path, round(last_query_time) * 1000, self.period)

        if round(dt.datetime.now().timestamp() * 1000) - round(last_query_time * 1000) > int(self.period):
            return True

        return False

    def __load_article_from_cache(self, cache_key):
        article_data = read_feed_item_from_cache(cache_key)
        if not article_data:
            return None

        entry = FeedItem(
            title=article_data.get("title"),
            link=article_data.get("link"),
            description=article_data.get("description"),
            author=article_data.get("author"),
            guid=article_data.get("guid"),
            created_time=self.__parse_created_time(article_data.get("created_time")),
            with_content=article_data.get("with_content", False)
        )
        entry.cache_key = cache_key
        return entry

    @staticmethod
    def __parse_created_time(value):
        if not value:
            return None

        try:
            return datetime.fromisoformat(value)
        except ValueError:
            logging.warning(f"Unable to parse created_time from cache: {value}")
            return None

    @staticmethod
    def __build_metadata_list(metadata_dicts):
        if not metadata_dicts:
            return []

        metadata_objects = []
        for metadata_dict in metadata_dicts:
            required = ["title", "link", "guid"]
            missing = [f for f in required if f not in metadata_dict]
            if missing:
                logging.error("Router metadata dict missing required fields %s: %s", missing, metadata_dict)
                continue
            if "json_name" in metadata_dict and "cache_key" not in metadata_dict:
                metadata_dict["cache_key"] = metadata_dict.pop("json_name")
            metadata_objects.append(Metadata(**metadata_dict))
        return metadata_objects

    @staticmethod
    def __write_article_list_to_cache(cache_key, article_metadata_list):
        write_metadata_list(cache_key, article_metadata_list)
