import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import redis
import yaml


DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def _log_cache(level, message, *args, exc_info=None):
    logging.log(level, "[cache] " + message, *args, exc_info=exc_info)


@dataclass(frozen=True)
class CacheConfig:
    redis_url: str = DEFAULT_REDIS_URL


def load_cache_config():
    config_path = _find_config_path()
    config_data = {}

    if config_path is not None:
        try:
            with open(config_path) as config_file:
                config_data = yaml.safe_load(config_file) or {}
                _log_cache(logging.INFO, "loaded config path=%s", config_path)
        except yaml.YAMLError as exc:
            _log_cache(logging.WARNING, "failed to parse config path=%s error=%s using_defaults=true", config_path, exc)
    else:
        _log_cache(
            logging.WARNING,
            "config not found repo_root=%s cwd=%s using_defaults=true",
            Path(__file__).resolve().parents[1],
            Path.cwd(),
        )

    redis_url = os.environ.get("RSS_REDIS_URL") or config_data.get("rss_redis_url") or DEFAULT_REDIS_URL
    return CacheConfig(redis_url=redis_url)


def _find_config_path():
    root_dir = Path(__file__).resolve().parents[1]
    candidate_paths = (
        root_dir / "config.yml",
        Path.cwd() / "config.yml",
    )

    for path in candidate_paths:
        if path.exists():
            return path

    return None


class CacheStore:
    def __init__(self, config=None):
        self.config = config or load_cache_config()
        self._redis_client = None
        self._connection_attempted = False

    def ensure_connection(self):
        client = self._get_client()
        client.ping()
        return client

    @staticmethod
    def metadata_list_key(cache_key):
        return f"{cache_key}:metadata-list"

    @staticmethod
    def build_time_key(cache_key):
        return f"build-time:{cache_key}"

    def read_metadata_list(self, cache_key):
        client = self._get_client()
        try:
            raw = client.get(self.metadata_list_key(cache_key))
            if raw is None:
                return None
            return json.loads(raw)
        except (redis.RedisError, json.JSONDecodeError) as exc:
            self._log_error("read metadata list", exc)
            return None

    def write_metadata_list(self, cache_key, metadata_list):
        client = self._get_client()
        try:
            payload = json.dumps([self._metadata_to_dict(metadata) for metadata in metadata_list])
            client.set(self.metadata_list_key(cache_key), payload)
        except (redis.RedisError, TypeError) as exc:
            self._log_error("write metadata list", exc)

    def write_feed_item(self, key, payload):
        client = self._get_client()
        try:
            client.set(key, json.dumps(payload))
        except (redis.RedisError, TypeError) as exc:
            self._log_error("write feed item", exc)

    def read_feed_item(self, key):
        client = self._get_client()
        try:
            raw = client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except (redis.RedisError, json.JSONDecodeError) as exc:
            self._log_error("read feed item", exc)
            return None

    def read_build_time(self, cache_key):
        client = self._get_client()
        try:
            raw = client.get(self.build_time_key(cache_key))
            if raw is None:
                return None
            return datetime.fromisoformat(raw)
        except (redis.RedisError, ValueError) as exc:
            self._log_error("read build time", exc)
            return None

    def write_build_time(self, cache_key, value):
        client = self._get_client()
        try:
            if isinstance(value, datetime):
                client.set(self.build_time_key(cache_key), value.isoformat())
        except redis.RedisError as exc:
            self._log_error("write build time", exc)

    def _get_client(self):
        if self._connection_attempted:
            return self._redis_client

        self._connection_attempted = True
        try:
            _log_cache(logging.INFO, "connecting redis_url=%s", self.config.redis_url)
            self._redis_client = redis.from_url(self.config.redis_url, decode_responses=True)
        except redis.RedisError as exc:
            _log_cache(logging.ERROR, "connect_failed redis_url=%s error=%s", self.config.redis_url, exc)
            raise

        return self._redis_client

    @staticmethod
    def _metadata_to_dict(metadata):
        metadata_dict = dict(metadata.__dict__)
        created_time = metadata_dict.get("created_time")
        if isinstance(created_time, datetime):
            metadata_dict["created_time"] = created_time.isoformat()
        return metadata_dict

    @staticmethod
    def _log_error(action, exc):
        _log_cache(logging.ERROR, "operation_failed action=%s error=%s", action, exc)


cache_store = CacheStore()


def ensure_cache_connection():
    return cache_store.ensure_connection()


def read_metadata_list(cache_key):
    return cache_store.read_metadata_list(cache_key)


def write_metadata_list(cache_key, metadata_list):
    cache_store.write_metadata_list(cache_key, metadata_list)


def read_feed_item_from_cache(key):
    return cache_store.read_feed_item(key)


def write_feed_item_to_cache(key, payload):
    cache_store.write_feed_item(key, payload)


def read_build_time(cache_key):
    return cache_store.read_build_time(cache_key)


def write_build_time(cache_key, value):
    cache_store.write_build_time(cache_key, value)
