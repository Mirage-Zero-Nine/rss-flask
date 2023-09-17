import logging

from flask import make_response

from data.feed_item_object import FeedItem
from data.rss_cache import feed_item_cache, feed_cache
from utils.cache_utilities import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.router_constants import jandan_query_period, jandan_page_prefix, html_parser, jandan_time_convert_pattern
from utils.time_converter import convert_time_with_pattern

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.INFO)


def get_feed_item_list():
    soup = get_link_content_with_bs_no_params(jandan_page_prefix, html_parser)
    post_list = soup.find_all(
        "div",
        {"class": "post f list-post"}
    )  # type is bs4.element.ResultSet
    feed_item_list = []

    for post in post_list:
        title = post.find('h2').text
        link = post.find('h2').find('a')['href']
        author = post.find_all(
            "div",
            {"class": "time_s"}
        )[0].find('a').text

        if "日好价" not in title:
            if link in feed_item_cache.keys():
                feed_item = feed_item_cache[link]
            else:
                feed_item = FeedItem(title=title,
                                     link=link,
                                     author=author,
                                     guid=link,
                                     with_content=False)

            feed_item_list.append(feed_item)

    return feed_item_list


def get_individual_post_content(post_list):
    for post in post_list:
        if post.with_content is False:
            soup = get_link_content_with_bs_no_params(post.link, html_parser)
            description_list = soup.find_all(
                "div",
                {"class": "post f"}
            )  # type is bs4.element.ResultSet

            # created time sample:
            # 2022.03.13 , 14:32
            created_time = description_list[0].find_all(
                "div",
                {"class": "time_s"}
            )[0].text.split('@')[1].strip()
            post.created_time = convert_time_with_pattern(created_time, jandan_time_convert_pattern, 8)
            description_string = ''
            for paragraph in description_list:
                for p in paragraph.find_all('p'):
                    description_string += str(p)
            post.description = description_string
            post.with_content = True

            feed_item_cache[post.guid] = post


def generate_feed_rss():
    item_list = get_feed_item_list()
    get_individual_post_content(item_list)
    feed = generate_feed_object(
        title="煎蛋",
        link=jandan_page_prefix,
        description="煎蛋 - 地球上没有新鲜事",
        language="zh-cn",
        feed_item_list=item_list
    )

    return feed


def get_rss_xml_response():
    """
    Entry point of the router.
    Currently, currency_name is not used.
    :return: XML feed
    """
    jandan_key = 'jandan/latest'
    should_query_website = check_query(jandan_key, jandan_query_period,"jandan")
    if should_query_website is True:
        feed = generate_feed_rss()
        feed_cache[jandan_key] = feed
    else:
        feed = feed_cache[jandan_key]

    response_currency = make_response(feed.rss())
    response_currency.headers.set('Content-Type', 'application/rss+xml')

    return response_currency


if __name__ == '__main__':
    pass
