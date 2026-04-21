import datetime as dt
import logging
from datetime import datetime

import pytz
from flask import make_response

from utils.cache_store import (
    read_build_time,
    read_feed_item_from_cache,
    read_metadata_list,
    write_build_time,
    write_metadata_list,
)
from utils.feed_item_object import (
    FeedItem,
    Metadata,
    convert_router_path_to_save_path_prefix,
    generate_json_name,
)
from utils.log_context import format_router_log_prefix, router_log_context
from utils.xml_utilities import generate_feed_object_for_new_router


class BaseRouter:
    def __init__(
        self,
        router_path="",
        feed_title="",
        original_link="",
        articles_link="",
        description="",
        language="",
        period=1000,
    ):
        self.router_path = router_path
        self.feed_title = feed_title
        self.original_link = original_link
        self.articles_link = articles_link
        self.description = description
        self.language = language
        self.period = period

    @property
    def router_name(self):
        return self.__class__.__name__

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        return []

    def _get_article_content(self, article_metadata, entry):
        pass

    def get_rss_xml_response(self, parameter=None, link_filter=None, title_filter=None):
        with router_log_context(self.router_name, self.router_path, "serve-cache"):
            cache_key = self._generate_cache_key_for_router(parameter)
            self._log_info(f"serve cached rss cache_key={cache_key}")
            article_metadata_list = self._load_cached_metadata_list(cache_key)
            last_build_time = read_build_time(cache_key) or dt.datetime.now(pytz.timezone("GMT"))
            feed_entries_list = self._build_cached_feed_entries(article_metadata_list)
            feed = self._generate_response(
                last_build_time=last_build_time,
                feed_entries_list=feed_entries_list,
                parameter=parameter,
            )
            self._log_info(
                f"serve completed cache_key={cache_key} item_count={len(feed_entries_list)} "
                f"last_build_date={feed.lastBuildDate}"
            )

            response = make_response(feed.rss())
            response.headers.set("Content-Type", "application/rss+xml")
            return response

    def refresh_cache(self, parameter=None, link_filter=None, title_filter=None):
        with router_log_context(self.router_name, self.router_path, "refresh-cache"):
            cache_key = self._generate_cache_key_for_router(parameter)
            self._log_info(f"refresh start cache_key={cache_key}")
            article_metadata_list = self._get_articles_list(
                parameter=parameter,
                link_filter=link_filter,
                title_filter=title_filter,
            )
            self._write_article_list_to_cache(self._build_article_list_key(cache_key), article_metadata_list)

            refreshed_count = 0
            for article_metadata in article_metadata_list:
                try:
                    entry = self._refresh_article_cache(article_metadata)
                    if entry is not None and entry.description is not None:
                        refreshed_count += 1
                except Exception as exc:
                    self._log_error(
                        f"refresh article failed cache_key={article_metadata.json_name} "
                        f"article_url={article_metadata.link} error={exc}"
                    )

            last_build_time = dt.datetime.now(pytz.timezone("GMT"))
            write_build_time(cache_key, last_build_time)
            self._log_info(
                f"refresh completed cache_key={cache_key} metadata_count={len(article_metadata_list)} "
                f"content_count={refreshed_count} last_build_time={last_build_time.isoformat()}"
            )
            return {
                "cache_key": cache_key,
                "metadata_count": len(article_metadata_list),
                "content_count": refreshed_count,
                "last_build_time": last_build_time,
            }

    def has_cached_feed(self, parameter=None):
        with router_log_context(self.router_name, self.router_path, "warmup-check"):
            cache_key = self._generate_cache_key_for_router(parameter)
            article_metadata_list = self._load_cached_metadata_list(cache_key)
            if not article_metadata_list:
                self._log_info(f"warmup check empty metadata cache_key={cache_key}")
                return False

            cached_article_count = 0
            for article_metadata in article_metadata_list:
                if self._load_article_from_cache(article_metadata.json_name) is not None:
                    cached_article_count += 1

            has_cache = cached_article_count > 0
            self._log_info(
                f"warmup check cache_key={cache_key} metadata_count={len(article_metadata_list)} "
                f"cached_article_count={cached_article_count} has_cache={has_cache}"
            )
            return has_cache

    def _generate_response(self, last_build_time, feed_entries_list, parameter):
        return generate_feed_object_for_new_router(
            title=self.feed_title,
            link=self.original_link,
            description=self.description,
            language=self.language,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list,
        )

    def _generate_cache_key_for_router(self, parameter=None):
        if parameter is None:
            return self.router_path
        values = [str(value) for value in parameter.values()]
        return f"{self.router_path}/{'/'.join(values)}"

    def _build_article_list_key(self, cache_key):
        save_path_prefix = convert_router_path_to_save_path_prefix(cache_key)
        return generate_json_name(save_path_prefix, self.feed_title)

    def _load_article_from_cache(self, cache_key):
        article_data = read_feed_item_from_cache(cache_key)
        if not article_data:
            return None

        entry = FeedItem(
            title=article_data.get("title"),
            link=article_data.get("link"),
            description=article_data.get("description"),
            author=article_data.get("author"),
            guid=article_data.get("guid"),
            created_time=self._parse_created_time(article_data.get("created_time")),
            with_content=article_data.get("with_content", False),
        )
        entry.json_name = cache_key
        return entry

    def _refresh_article_cache(self, article_metadata):
        with router_log_context(
            self.router_name,
            self.router_path,
            "refresh-article",
            target_url=article_metadata.link,
        ):
            self._log_info(f"refresh article cache_key={article_metadata.json_name}")
            entry = FeedItem(
                title=article_metadata.title,
                link=article_metadata.link,
                guid=article_metadata.guid or article_metadata.link,
            )
            self._get_article_content(article_metadata, entry)
            return entry

    def _load_cached_metadata_list(self, cache_key):
        article_list_key = self._build_article_list_key(cache_key)
        cached_metadata = read_metadata_list(article_list_key)
        if not cached_metadata:
            self._log_warning(f"cache miss metadata cache_key={cache_key} metadata_key={article_list_key}")
            return []

        metadata_objects = self._build_metadata_list(cached_metadata)
        self._log_info(
            f"loaded cached metadata cache_key={cache_key} metadata_key={article_list_key} "
            f"count={len(metadata_objects)}"
        )
        return metadata_objects

    def _build_cached_feed_entries(self, article_metadata_list):
        feed_entries_list = []
        for article_metadata in article_metadata_list:
            with router_log_context(
                self.router_name,
                self.router_path,
                "serve-article-cache",
                target_url=article_metadata.link,
            ):
                entry = self._load_article_from_cache(article_metadata.json_name)
                if entry is None:
                    self._log_warning(f"cache miss article cache_key={article_metadata.json_name}")
                    continue
                if entry.description is None:
                    self._log_warning(
                        f"skip cached article with empty description cache_key={article_metadata.json_name}"
                    )
                    continue
                feed_entries_list.append(entry)
        return feed_entries_list

    @staticmethod
    def _parse_created_time(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            logging.warning("%s unable_to_parse_created_time value=%s", format_router_log_prefix(), value)
            return None

    @staticmethod
    def _build_metadata_list(metadata_dicts):
        return [Metadata(**metadata_dict) for metadata_dict in metadata_dicts]

    @staticmethod
    def _write_article_list_to_cache(cache_key, article_metadata_list):
        write_metadata_list(cache_key, article_metadata_list)

    def _log_info(self, message):
        logging.info("%s %s", format_router_log_prefix(), message)

    def _log_warning(self, message):
        logging.warning("%s %s", format_router_log_prefix(), message)

    def _log_error(self, message):
        logging.error("%s %s", format_router_log_prefix(), message)
