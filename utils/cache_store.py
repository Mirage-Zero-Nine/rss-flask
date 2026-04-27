import json
import logging
import os

import redis
from datetime import datetime

from utils.router_constants import (
    metadata_list_ttl_seconds,
    feed_item_ttl_seconds,
    last_build_time_ttl_seconds,
)

from utils.config import load_config

config_data = load_config()

DEFAULT_REDIS_URL = os.environ.get("RSS_REDIS_URL") or config_data.get("rss_redis_url") or "redis://localhost:6379/0"

try:
    logging.info(f"Connecting to Redis at {DEFAULT_REDIS_URL}")
    _redis_client = redis.from_url(DEFAULT_REDIS_URL, decode_responses=True)
    _redis_client.ping()  # verify connectivity at import time
    logging.info("Redis connected successfully")
except redis.RedisError as exc:
    logging.warning(f"Unable to connect to redis at {DEFAULT_REDIS_URL}: {exc}")
    logging.warning("Redis is unavailable; cache functions will be no-ops.")
    _redis_client = None

def _has_client():
    return _redis_client is not None


def _log_error(action, exc):
    logging.error(f"Redis {action} failed: {exc}")


def metadata_list_key(cache_key):
    return f"{cache_key}:metadata-list"


def router_last_build_time_key(cache_key):
    return f"{cache_key}:last-build-time"


def read_metadata_list(cache_key):
    if not _has_client():
        return None

    try:
        raw = _redis_client.get(metadata_list_key(cache_key))
        if raw is None:
            return None

        return json.loads(raw)
    except (redis.RedisError, json.JSONDecodeError) as exc:
        _log_error("read metadata list", exc)
        return None


def write_metadata_list(cache_key, metadata_list, ttl_seconds=None):
    if ttl_seconds is None:
        ttl_seconds = metadata_list_ttl_seconds

    if not _has_client():
        return

    try:
        payload = json.dumps([_metadata_to_dict(metadata) for metadata in metadata_list])
        _redis_client.set(metadata_list_key(cache_key), payload, ex=ttl_seconds)
    except (redis.RedisError, TypeError) as exc:
        _log_error("write metadata list", exc)


def _metadata_to_dict(metadata):
    metadata_dict = dict(metadata.__dict__)
    created_time = metadata_dict.get("created_time")
    if isinstance(created_time, datetime):
        metadata_dict["created_time"] = created_time.isoformat()
    return metadata_dict


def read_last_build_time(cache_key):
    if not _has_client():
        return None

    try:
        raw = _redis_client.get(router_last_build_time_key(cache_key))
        if raw is None:
            return None

        return datetime.fromisoformat(raw)
    except (redis.RedisError, ValueError) as exc:
        _log_error("read last build time", exc)
        return None


def write_last_build_time(cache_key, last_build_time, ttl_seconds=None):
    if ttl_seconds is None:
        ttl_seconds = last_build_time_ttl_seconds

    if not _has_client():
        return

    try:
        value = last_build_time.isoformat() if isinstance(last_build_time, datetime) else str(last_build_time)
        _redis_client.set(router_last_build_time_key(cache_key), value, ex=ttl_seconds)
    except redis.RedisError as exc:
        _log_error("write last build time", exc)


def write_feed_item_to_cache(key, payload, ttl_seconds=None):
    if ttl_seconds is None:
        ttl_seconds = feed_item_ttl_seconds

    if not _has_client():
        logging.error("Redis client unavailable; feed item write skipped for key=%s", key)
        return

    try:
        _redis_client.set(key, json.dumps(payload), ex=ttl_seconds)
    except (redis.RedisError, TypeError) as exc:
        _log_error("write feed item", exc)


def read_feed_item_from_cache(key):
    if not _has_client():
        return None

    try:
        raw = _redis_client.get(key)
        if raw is None:
            return None

        return json.loads(raw)
    except (redis.RedisError, json.JSONDecodeError) as exc:
        _log_error("read feed item", exc)
        return None
