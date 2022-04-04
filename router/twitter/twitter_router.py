import requests
import logging

from flask import make_response
from datetime import datetime

import utils.router_constants as c
import utils.generate_xml as gxml
import utils.time_converter as tc
import router.twitter.twitter_utils as tu
import utils.check_if_valid as civ
import data.feed_item_object as do
import data.rss_cache as fc

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


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


def build_item_list(feed_item_list, data, user_name, request_arg):
    exclude_retweet = False
    exclude_reply = False
    try:
        exclude_retweet = request_arg[c.exclude_retweet]
    except KeyError:
        logging.info("Not getting excludeRetweet parameter. Treated as false.")

    try:
        exclude_reply = request_arg[c.exclude_reply]
    except KeyError:
        logging.info("Not getting excludeReply parameter. Treated as false.")

    for tweet_item in data[c.data]:
        tweet_url = c.tweet_link_prefix + tweet_item["id"]
        is_retweet = False
        is_reply = False
        try:
            tweet_type = tweet_item[c.referenced_tweet][0][c.reference_tweet_type]
            if tweet_type == c.retweet:
                is_retweet = True
            if tweet_type == c.replied_to:
                is_reply = True
        except KeyError:
            logging.info("no reference_tweet found.")

        if exclude_retweet and is_retweet:
            continue
        elif exclude_reply and is_reply:
            continue
        else:
            feed_item = do.FeedItem(
                title=tu.generate_title(tweet_item["text"]),
                link=tweet_url,
                description=tweet_item["text"],
                author=user_name,
                guid=tweet_url,
                created_time=tc.convert_time_twitter(tweet_item[c.created_at]),
            )
            feed_item_list.append(feed_item)


def generate_rss_feed(user_name, request_arg):
    """
    :param user_name:
    :return: used in cache value, so return feed object instead of rss string.
    """
    user_id = get_twitter_user_id_by_name(user_name)
    item_list = []
    response = None
    for i in range(0, c.twitter_query_page_count):
        if i == 0:
            response = get_requested_user_timeline_list_by_user_id(user_id, None)
        else:
            next_page_token = response[c.meta][c.next_token]
            response = get_requested_user_timeline_list_by_user_id(user_id, next_page_token)
        build_item_list(item_list, response, user_name, request_arg)

    # build_item_list(item_list, response, user_name)
    # next_page_token = response[c.meta][c.next_token]
    # response = get_requested_user_timeline_list_by_user_id(user_id, next_page_token)
    # build_item_list(item_list, response, user_name)

    feed = gxml.generate_feed_object(
        title="Twitter - " + user_name,
        link=c.twitter_prefix + user_name,
        description="Tweet from " + user_name,
        language="en-US",
        feed_item_list=item_list
    )
    logging.debug("user name: " + user_name)

    return feed


def check_if_should_query(cache_key):
    """
    Limit query to at most 1 time in 10 minutes.
    1. Check if the username exist in cache (initially, cache does not contain anything)
    2. key in cache: username, value: feed under this user
    3. Check if current call is longer than 10 minutes based on build time of feed
    4. If so, query Twitter api and update feed object in cache, otherwise, return the feed directly.
    :return: if service should query now
    """

    # no item in cache or the query username does not exist
    if len(fc.feed_cache) == 0 or cache_key not in fc.feed_cache.keys() or civ.check_should_query_twitter(
            datetime.timestamp(fc.feed_cache[cache_key].lastBuildDate),
            c.twitter_query_period):
        return True

    return False


def generate_rss_xml_response(user_name, request_arg):
    """
    Entry point of the router.
    Check if current call needs to query (1 time in 10 minutes at most), then query Twitter API.
    :param user_name:
    :param request_arg: request parameters, including exclude retweet/reply
    :return: xml response
    """

    cache_key = 'twitter/' + user_name

    should_call_api = check_if_should_query(cache_key)
    logging.debug(
        "Query Twitter user " + user_name + " for this call: " + str(should_call_api)
    )
    # logging.debug("cache: " + str(fc.feed_cache))

    if should_call_api is True:
        feed = generate_rss_feed(user_name, request_arg)  # update Twitter feed by Twitter username
        fc.feed_cache[cache_key] = feed  # update cache by cache key
    else:
        feed = fc.feed_cache[cache_key]

    response_twitter = make_response(feed.rss())
    response_twitter.headers.set('Content-Type', 'application/rss+xml')
    return response_twitter


if __name__ == "__main__":
    print("main")
    print(generate_rss_xml_response("MacRumors"))
