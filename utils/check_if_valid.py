import time
import logging

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def clean_outdated_post(cache):
    # assuming the gap between each query will not be longer than 4 days
    current_millis = round(time.time() * 1000)
    four_days_in_millisecond = 259200000
    remove_key_list = []
    for key in cache:
        if current_millis - cache[key] > four_days_in_millisecond:
            remove_key_list.append(key)

    for key in remove_key_list:
        del cache[key]


def check_should_query(bool_state, last_query_time, cooldown_period):
    logging.info("last query time: " + str(round(last_query_time)))
    logging.info("current time: " + str(round(time.time() * 1000)))
    logging.info("cooldown: " + str(cooldown_period))

    if bool_state is None or round(time.time() * 1000) - round(last_query_time) > cooldown_period:
        return True

    return False


def check_should_query_no_state(last_query_time, cooldown_period):
    logging.info("last query time: " + str(round(last_query_time) * 1000))
    logging.info("current time: " + str(round(time.time() * 1000)))
    logging.info("cooldown period: " + str(cooldown_period))

    if round(time.time() * 1000) - round(last_query_time * 1000) > cooldown_period:
        return True

    return False


def check_should_query_twitter(last_query_time, cooldown_period):
    logging.info("current time: " + str(round(time.time() * 1000)))
    logging.info("last query time: " + str(round(last_query_time * 1000)))
    logging.info("cooldown: " + str(cooldown_period))

    """
    time.time() return time in second, to align with the cooldown period (which is in millisecond),
    hence, multiple 1000 to current time.
    Note in Twitter feed, the lastBuildTime stored in second.
    """
    if round(time.time() * 1000) - round(last_query_time * 1000) > cooldown_period:
        return True

    return False

# if __name__ == '__main__':
#     clean_outdated_post(None)
