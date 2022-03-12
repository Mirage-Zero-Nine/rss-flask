import requests
import router.twitter.twitter_utils as tu
import logging

from flask import make_response

import constant.constants as c
import utils.generate_xml as gxml
import utils.time_converter as tc

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


def build_item_list(item_list, data, user_name):
    for entry in data[c.data]:
        tweet_url = c.tweet_link_prefix + entry["id"]
        item = gxml.create_item(
            title=entry[c.created_at],
            link=tweet_url,
            description=entry["text"],
            author=user_name,
            guid=tweet_url,
            pubDate=tc.convert_time_twitter(entry[c.created_at]),
            isPermaLink=False
        )
        item_list.append(item)


def generate_rss_xml(user_name):
    user_id = get_twitter_user_id_by_name(user_name)
    response = get_requested_user_timeline_list_by_user_id(user_id, None)
    item_list = []
    build_item_list(item_list, response, user_name)
    next_page_token = response[c.meta][c.next_token]
    get_requested_user_timeline_list_by_user_id(user_id, next_page_token)

    feed = gxml.generate_feed(
        title="Seattle PD Twitter",
        link=c.twitter_prefix + user_name,
        description="Tweet from " + user_name,
        language="en-US",
        items=item_list
    )
    response = make_response(feed)
    response.headers.set('Content-Type', 'application/rss+xml')

    return response


if __name__ == "__main__":
    print("main")
    tu.get_config_variable(c.twitter_token)
