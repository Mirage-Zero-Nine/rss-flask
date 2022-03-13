import requests
import logging
import time

from flask import make_response

import constant.constants as c
import utils.generate_xml as gxml
import utils.time_converter as tc
import router.twitter.twitter_utils as tu
import utils.check_if_valid as civ

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)
started_time_twitter = round(time.time() * 1000)
minutes_in_millisecond_10 = 600  # 10 minutes in millisecond
should_query_twitter = None
response_twitter = None
cache = {}  # cache Twitter username and the last time this user was called


def call_twitter_api(url_type, url_params, request_params):
    url = tu.generate_url(url_type, url_params)
    response = requests.request("GET", url, auth=tu.bearer_oauth, params=request_params)
    logging.info("Request status code: " + str(response.status_code))
    if response.status_code != 200:
        raise Exception("Request returned an error: {} {}".format(response.status_code, response.text))
    return response.json()


def get_twitter_user_id_by_name(user_name):
    json_response = call_twitter_api(c.get_user_id_by_user_name, user_name, None)
    return json_response["data"]["id"]


def get_requested_user_timeline_list_by_user_id(user_id, next_page_token):
    if next_page_token is None:
        params = tu.get_params()
    else:
        params = tu.get_params_with_next_page_token(next_page_token)
    json_response = call_twitter_api(c.get_tweet_by_user_id, user_id, params)
    # print(json.dumps(json_response, indent=4, sort_keys=True))

    return json_response


def get_tweet_by_tweet_id(tweet_id_list):
    tweet_list = []
    for tweet_id in tweet_id_list:
        json_response = call_twitter_api(c.get_tweet_by_tweet_id, tweet_id, tu.get_params())
        tweet_list.append(json_response)

    return tweet_list


def build_item_list(item_list, data, user_name):
    for entry in data[c.data]:
        tweet_url = c.tweet_link_prefix + entry["id"]
        item = gxml.create_item(
            title=tu.generate_title(entry["text"]),
            link=tweet_url,
            description=entry["text"],
            author=user_name,
            guid=tweet_url,
            pubDate=tc.convert_time_twitter(entry[c.created_at]),
            isPermaLink=False
        )
        item_list.append(item)


def update_feed(user_name):
    user_id = get_twitter_user_id_by_name(user_name)
    response = get_requested_user_timeline_list_by_user_id(user_id, None)
    item_list = []
    build_item_list(item_list, response, user_name)
    next_page_token = response[c.meta][c.next_token]
    get_requested_user_timeline_list_by_user_id(user_id, next_page_token)

    feed = gxml.generate_feed(
        title="Twitter - " + user_name,
        link=c.twitter_prefix + user_name,
        description="Tweet from " + user_name,
        language="en-US",
        items=item_list
    )
    logging.debug("user name: " + user_name)
    logging.debug("actual feed: " + feed)
    response = make_response(feed)
    response.headers.set('Content-Type', 'application/rss+xml')

    return response


def check_if_should_query(user_name):
    """
    Limit query to at most 1 time in 15 minutes.
    Todo: refactor this implementation by using redis to both dedup and limit query speed.
    :return: if service should query now
    """
    global should_query_twitter
    global started_time_twitter

    if len(cache) == 0 or user_name not in cache.keys():
        cache[user_name] = round(time.time() * 1000)  # put current time
        return True
    else:
        if civ.check_should_query_twitter(cache[user_name], minutes_in_millisecond_10):
            cache[user_name] = round(time.time() * 1000)
            return True

    return False


def generate_rss_xml(user_name):
    """
    Entry point of the router.
    Check if current call needs to query (1 time in 10 minutes at most), then query Twitter API.
    :param user_name:
    :return:
    """
    global response_twitter, started_time_twitter, user_name_check
    should_call_api = check_if_should_query(user_name)
    logging.info(
        "Should query Twitter user " + user_name + " for this call: " +
        str(should_call_api) +
        ", current start time: " +
        str(started_time_twitter)
    )
    if should_call_api is True:
        response_twitter = update_feed(user_name)

    return response_twitter


if __name__ == "__main__":
    print("main")
    print(generate_rss_xml("MacRumors"))
