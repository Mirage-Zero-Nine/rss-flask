import json
import logging
import os
import uuid
from collections import OrderedDict
from typing import Any, cast

import redis
from datetime import datetime

from utils.config import load_config
from utils.router_constants import (
    last_build_time_ttl_seconds,
    warm_lock_ttl_seconds,
)
config_data = load_config()

DEFAULT_REDIS_URL = os.environ.get("RSS_REDIS_URL") or config_data.get("rss_redis_url") or "redis://localhost:6379/0"
MetadataDict = dict[str, Any]
FeedItemPayload = dict[str, Any]
_NO_REDIS_LOCK_TOKEN = "no-redis-cache-lock"

try:
    logging.info("Connecting to Redis cache")
    _redis_client = redis.from_url(DEFAULT_REDIS_URL, decode_responses=True)
    _redis_client.ping()  # verify connectivity at import time
    logging.info("Redis connected successfully")
except redis.RedisError as exc:
    logging.warning("Unable to connect to redis: %s", exc)
    logging.warning("Redis is unavailable; cache functions will be no-ops.")
    _redis_client = None

def _has_client() -> bool:
    return _redis_client is not None


def _log_error(action: str, exc: Exception) -> None:
    logging.error(f"Redis {action} failed: {exc}")


def metadata_list_key(cache_key: str) -> str:
    return f"{cache_key}:metadata-list"


def router_last_build_time_key(cache_key: str) -> str:
    return f"{cache_key}:last-build-time"


def read_metadata_list(cache_key: str) -> list[MetadataDict] | None:
    if not _has_client():
        return None

    try:
        raw = _redis_client.get(metadata_list_key(cache_key))
        if raw is None:
            return None

        metadata = json.loads(raw)
        if not isinstance(metadata, list):
            logging.error("Redis metadata list for key=%s is not a list", cache_key)
            return None
        if not all(isinstance(item, dict) for item in metadata):
            logging.error("Redis metadata list for key=%s contains non-object items", cache_key)
            return None
        return cast(list[MetadataDict], metadata)
    except (redis.RedisError, json.JSONDecodeError) as exc:
        _log_error("read metadata list", exc)
        return None


def _metadata_identity(metadata_dict: MetadataDict) -> Any:
    return (
        metadata_dict.get("cache_key")
        or metadata_dict.get("guid")
        or metadata_dict.get("link")
        or metadata_dict.get("title")
    )


def _merge_metadata_dicts(existing_metadata: list[MetadataDict], incoming_metadata: list[MetadataDict]) -> list[MetadataDict]:
    merged: OrderedDict[Any, MetadataDict] = OrderedDict()

    for metadata_dict in incoming_metadata:
        identity = _metadata_identity(metadata_dict)
        if identity is None:
            identity = json.dumps(metadata_dict, sort_keys=True, ensure_ascii=False)
        merged[identity] = metadata_dict

    for metadata_dict in existing_metadata:
        identity = _metadata_identity(metadata_dict)
        if identity is None:
            identity = json.dumps(metadata_dict, sort_keys=True, ensure_ascii=False)
        if identity not in merged:
            merged[identity] = metadata_dict

    return list(merged.values())


def write_metadata_list(cache_key: str, metadata_list: list[Any]) -> None:
    if not _has_client():
        return

    try:
        incoming_metadata = [_metadata_to_dict(metadata) for metadata in metadata_list]
        existing_metadata = read_metadata_list(cache_key) or []
        merged_metadata = _merge_metadata_dicts(existing_metadata, incoming_metadata)
        payload = json.dumps(merged_metadata)
        _redis_client.set(metadata_list_key(cache_key), payload)
    except (redis.RedisError, TypeError) as exc:
        _log_error("write metadata list", exc)


def replace_metadata_list(cache_key: str, metadata_list: list[Any]) -> None:
    if not _has_client():
        return

    try:
        payload = json.dumps([_metadata_to_dict(metadata) for metadata in metadata_list])
        _redis_client.set(metadata_list_key(cache_key), payload)
    except (redis.RedisError, TypeError) as exc:
        _log_error("replace metadata list", exc)


def acquire_cache_lock(lock_name: str, ttl_seconds: int = 120) -> str | None:
    if not _has_client():
        return _NO_REDIS_LOCK_TOKEN

    token = uuid.uuid4().hex
    lock_key = f"cache_lock:{lock_name}"
    try:
        result = _redis_client.set(lock_key, token, nx=True, ex=ttl_seconds)
        if result is True or result == 1:
            return token
        return None
    except redis.RedisError as exc:
        logging.warning("Failed to acquire cache lock for %s: %s. Allowing local execution.", lock_name, exc)
        return _NO_REDIS_LOCK_TOKEN


def release_cache_lock(lock_name: str, token: str) -> None:
    if not _has_client() or token == _NO_REDIS_LOCK_TOKEN:
        return

    lock_key = f"cache_lock:{lock_name}"
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    end
    return 0
    """
    try:
        _redis_client.eval(script, 1, lock_key, token)
    except redis.RedisError as exc:
        logging.warning("Failed to release cache lock for %s: %s", lock_name, exc)


def acquire_warm_lock(job_name: str) -> bool:
    if not _has_client():
        return True

    lock_key = f"warm_lock:{job_name}"
    try:
        result = _redis_client.set(lock_key, "1", nx=True, ex=warm_lock_ttl_seconds)
        return result is True or result == 1
    except redis.RedisError as exc:
        logging.warning("Failed to acquire warm lock for %s: %s. Allowing warm to proceed.", job_name, exc)
        return True


def release_warm_lock(job_name: str) -> None:
    if not _has_client():
        return

    lock_key = f"warm_lock:{job_name}"
    try:
        _redis_client.delete(lock_key)
    except redis.RedisError:
        pass


def _metadata_to_dict(metadata: Any) -> MetadataDict:
    metadata_dict = dict(metadata.__dict__)
    created_time = metadata_dict.get("created_time")
    if isinstance(created_time, datetime):
        metadata_dict["created_time"] = created_time.isoformat()
    return metadata_dict


def read_last_build_time(cache_key: str) -> datetime | None:
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


def write_last_build_time(cache_key: str, last_build_time: datetime, ttl_seconds: int | None = None) -> None:
    if ttl_seconds is None:
        ttl_seconds = last_build_time_ttl_seconds

    if not _has_client():
        return

    try:
        value = last_build_time.isoformat() if isinstance(last_build_time, datetime) else str(last_build_time)
        _redis_client.set(router_last_build_time_key(cache_key), value, ex=ttl_seconds)
    except redis.RedisError as exc:
        _log_error("write last build time", exc)


def write_feed_item_to_cache(key: str, payload: FeedItemPayload) -> None:
    if not _has_client():
        logging.error("Redis client unavailable; feed item write skipped for key=%s", key)
        return

    try:
        _redis_client.set(key, json.dumps(payload))
    except (redis.RedisError, TypeError) as exc:
        _log_error("write feed item", exc)


def read_feed_item_from_cache(key: str | None) -> FeedItemPayload | None:
    if key is None:
        return None

    if not _has_client():
        return None

    try:
        raw = _redis_client.get(key)
        if raw is None:
            return None

        payload = json.loads(raw)
        if not isinstance(payload, dict):
            logging.error("Redis feed item for key=%s is not an object", key)
            return None
        return cast(FeedItemPayload, payload)
    except (redis.RedisError, json.JSONDecodeError) as exc:
        _log_error("read feed item", exc)
        return None
