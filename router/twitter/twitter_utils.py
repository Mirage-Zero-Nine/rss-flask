import yaml

from constant import constants as c

"""
static methods for twitter router
"""


def generate_url(url_type, param):
    if url_type == c.get_user_id_by_user_name:
        return "https://api.twitter.com/2/users/by/username/{}".format(param)
    elif url_type == c.get_tweet_by_user_id:
        return "https://api.twitter.com/2/users/{}/tweets".format(param)
    elif url_type == c.get_tweet_by_tweet_id:
        return "https://api.twitter.com/2/tweets/{}".format(param)
    else:
        raise ValueError("incorrect request url type: {}".format(url_type))


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


def get_config_variable(para):
    # arr = os.listdir()
    # file path started from app.py
    with open('authentication.yaml') as f:
        # use safe_load instead load
        config = yaml.safe_load(f)
        return config[c.token][para]


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    Note: you will need to add your own token by adding a authentication.yaml at the project root (same as app.py).
    """
    token = get_config_variable(c.twitter_token)
    if token is None:
        raise Exception("Token was not set!")
    r.headers["Authorization"] = f"Bearer {token}"
    r.headers["User-Agent"] = "v2UserTweetsPython"
    return r


def generate_title(title_string):
    if len(title_string) > 50:
        return title_string[:50] + "..."

    return title_string


if __name__ == '__main__':
    print(generate_title("test"))
    print(generate_title("testtesttesttesttesttesttesttesttesttesttest"))
