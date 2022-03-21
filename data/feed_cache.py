"""
In-memory cache to cache the latest queried feed object to reduce web API call.
General idea:
- key: parameter of router (e.g.: Twitter username for Twitter route)
- value: feed item object
Usage:
- If the cache is empty, or the key does not exist in cache, then directly call query function in router.
- If it contains the request key, then check the latest build date to see if the service needs to call query function.
"""

feed_cache = {}
