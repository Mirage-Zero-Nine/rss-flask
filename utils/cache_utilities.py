from datetime import datetime
import logging
import data.rss_cache
import time


def check_query(key, period, name):
    should_refresh = (len(data.rss_cache.feed_cache) == 0
                      or key not in data.rss_cache.feed_cache.keys()
                      or check_should_query_no_state(datetime.timestamp(data.rss_cache.feed_cache[key].lastBuildDate),
                                                     period))

    logging.info(f"Query {name} for this call: {should_refresh}")

    return should_refresh


def check_should_query_no_state(last_query_time, cooldown_period):
    logging.info("last query time: " + str(round(last_query_time) * 1000))
    logging.info("current time: " + str(round(time.time() * 1000)))
    logging.info("cooldown period: " + str(cooldown_period))

    if round(time.time() * 1000) - round(last_query_time * 1000) > cooldown_period:
        return True

    return False
