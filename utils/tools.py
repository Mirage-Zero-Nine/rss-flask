from datetime import datetime
import logging
import utils.rss_cache
import time


def format_author_names(author_list):
    if not author_list:
        return ""
    elif len(author_list) == 1:
        return author_list[0]
    else:
        return ', '.join(author_list)


def check_need_to_filter(link, title, link_filter, title_filter):
    if link_filter and link.startswith(link_filter):
        return True
    if title_filter and title.startswith(title_filter):
        return True

    return False


def check_query(key, period, name):
    """
    Check if current router needs to refresh. Unit of period is minute.
    :return: if the app need to refresh the content for this router
    """
    should_refresh = (len(utils.rss_cache.feed_cache) == 0
                      or key not in utils.rss_cache.feed_cache.keys()
                      or check_should_query_no_state(datetime.timestamp(utils.rss_cache.feed_cache[key].lastBuildDate),
                                                     period))

    logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Query {name} for this call: {should_refresh}")

    return should_refresh


def check_should_query_no_state(last_query_time, cooldown_period):
    logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Last query time: " + str(round(last_query_time) * 1000))
    logging.info(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Cooldown period: " + str(cooldown_period))

    if round(time.time() * 1000) - round(last_query_time * 1000) > cooldown_period:
        return True

    return False
