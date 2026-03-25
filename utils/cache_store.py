import json
import logging
import os

import redis
import yaml
from datetime import datetime
from pathlib import Path

_root_dir = Path(__file__).resolve().parents[1]
config_data = {}
config_path = _root_dir / "config.yml"
if not config_path.exists():
    fallback_path = Path.cwd() / "config.yml"
    if fallback_path != config_path and fallback_path.exists():
        config_path = fallback_path

if config_path.exists():
    try:
        with open(config_path) as config_file:
            config_data = yaml.safe_load(config_file) or {}
            logging.info(f"Loaded config.yml from {config_path}")
    except yaml.YAMLError as exc:
        logging.warning(f"Failed to parse config.yml at {config_path}: {exc}. Using defaults.")
else:
    logging.warning(f"config.yml not found at {_root_dir}/config.yml or {Path.cwd()}, using defaults.")

DEFAULT_REDIS_URL = os.environ.get("RSS_REDIS_URL") or config_data.get("rss_redis_url") or "redis://localhost:6379/0"

try:
    logging.info(f"Connecting to Redis at {DEFAULT_REDIS_URL}")
    _redis_client = redis.from_url(DEFAULT_REDIS_URL, decode_responses=True)
except redis.RedisError as exc:
    logging.error(f"Unable to connect to redis at {DEFAULT_REDIS_URL}: {exc}")
    _redis_client = None


def _has_client():
    return _redis_client is not None


def _log_error(action, exc):
    logging.error(f"Redis {action} failed: {exc}")


def metadata_list_key(cache_key):
    return f"{cache_key}:metadata-list"


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


def write_metadata_list(cache_key, metadata_list):
    if not _has_client():
        return

    try:
        payload = json.dumps([_metadata_to_dict(metadata) for metadata in metadata_list])
        _redis_client.set(metadata_list_key(cache_key), payload)
    except (redis.RedisError, TypeError) as exc:
        _log_error("write metadata list", exc)


def _metadata_to_dict(metadata):
    metadata_dict = dict(metadata.__dict__)
    created_time = metadata_dict.get("created_time")
    if isinstance(created_time, datetime):
        metadata_dict["created_time"] = created_time.isoformat()
    return metadata_dict


def write_feed_item_to_cache(key, payload):
    if not _has_client():
        return

    try:
        _redis_client.set(key, json.dumps(payload))
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
