"""
Build-time cache used to reduce repeated refresh work.
"""

from datetime import datetime

from utils.cache_store import read_string_from_cache, write_string_to_cache


class BuildTimeCache:
    @staticmethod
    def _cache_key(key):
        return f"build-time:{key}"

    def get(self, key, default=None):
        cached_value = read_string_from_cache(self._cache_key(key))
        if cached_value is not None:
            try:
                return datetime.fromisoformat(cached_value)
            except ValueError:
                return default

        return default

    def set(self, key, value):
        if isinstance(value, datetime):
            write_string_to_cache(self._cache_key(key), value.isoformat())


build_time_cache = BuildTimeCache()
