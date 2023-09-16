from datetime import datetime
import logging
import utils.router_constants
import utils.check_if_valid
import data.rss_cache


def check_query(key, period, name):
    should_refresh = (len(data.rss_cache.feed_cache) == 0
                      or key not in data.rss_cache.feed_cache.keys()
                      or utils.check_if_valid.check_should_query_no_state(datetime.timestamp(data.rss_cache.feed_cache[key].lastBuildDate), period))

    logging.info(f"Query {name} for this call: {should_refresh}")

    return should_refresh
