import requests
import json
import yaml
import os

from flask import make_response

from constant import constants as c
from utils import generate_xml as gxml


def get_config_variable(para):
    # arr = os.listdir()

    # file path started from app.py
    with open('authentication.yaml') as f:
        # use safe_load instead load
        config = yaml.safe_load(f)
        return config[c.token][para]


def get_params():
    # Tweet fields are adjustable.
    # Options include:
    # attachments, author_id, context_annotations,
    # conversation_id, created_at, entities, geo, id,
    # in_reply_to_user_id, lang, non_public_metrics, organic_metrics,
    # possibly_sensitive, promoted_metrics, public_metrics, referenced_tweets,
    # source, text, and withheld
    return {
        c.tweet_field: "referenced_tweets,created_at",
        c.expansions: "referenced_tweets.id"
    }


def get_params_with_next_page_token(pagination_token):
    return {
        c.tweet_field: "referenced_tweets,created_at",
        c.expansions: "referenced_tweets.id",
        c.pagination_token: pagination_token
    }


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """
    token = get_config_variable(c.twitter_token)
    if token is None:
        raise Exception("Token was not set!")
    r.headers["Authorization"] = f"Bearer {token}"
    r.headers["User-Agent"] = "v2UserTweetsPython"
    return r


def connect_to_endpoint(url, params):
    response = requests.request("GET", url, auth=bearer_oauth, params=params)
    print("Request status code: " + str(response.status_code))
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )

    return response.json()


def generate_url(url_type, param):
    if url_type == c.get_user_id_by_user_name:
        return "https://api.twitter.com/2/users/by/username/{}".format(param)
    elif url_type == c.get_tweet_by_user_id:
        return "https://api.twitter.com/2/users/{}/tweets".format(param)
    elif url_type == c.get_tweet_by_tweet_id:
        return "https://api.twitter.com/2/tweets/{}".format(param)
    else:
        raise ValueError("incorrect request url type: {}".format(url_type))


def __call_tweet_api(request_type, para):
    url = generate_url(request_type, para)
    return connect_to_endpoint(url, None)


def __call_tweet_api_with_para(request_type, url_para, api_para):
    url = generate_url(request_type, url_para)
    return connect_to_endpoint(url, api_para)


def get_twitter_user_id_by_name(user_name):
    json_response = __call_tweet_api(c.get_user_id_by_user_name, user_name)
    # print("user id: " + json_response["data"]["id"])
    return json_response["data"]["id"]


def get_requested_user_timeline_list_by_user_id(user_id, next_page_token):
    if next_page_token is None:
        params = get_params()
    else:
        params = get_params_with_next_page_token(next_page_token)
    json_response = __call_tweet_api_with_para(c.get_tweet_by_user_id, user_id, params)
    # print(json.dumps(json_response, indent=4, sort_keys=True))
    # id_list = []
    # for entry in json_response["data"]:
    #     # print(entry["id"])
    #     id_list.append(entry["id"])

    return json_response


def get_tweet_by_tweet_id(tweet_id_list):
    for tweet_id in tweet_id_list:
        json_response = __call_tweet_api(c.get_tweet_by_tweet_id, tweet_id)
        # print(json.dumps(json_response, indent=4, sort_keys=True))
    # print(json.dumps(json_response, indent=4, sort_keys=True))
    # return json_response


def build_item_list(item_list, data, user_name):
    for entry in data[c.data]:
        tweet_url = c.tweet_link_prefix + entry["id"]
        item = gxml.create_item(
            title=entry[c.created_at],
            link=tweet_url,
            description=entry["text"],
            author=user_name,
            guid=tweet_url,
            created_time_string=entry[c.created_at]
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
    # response.headers.set('Content-Type', 'application/rss+xml')

    return response


if __name__ == "__main__":
    # main()
    # print(os.environ['BEARER_TOKEN'])
    print("main")
    get_config_variable(c.twitter_token)
