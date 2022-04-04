import logging

from flask import make_response
from datetime import datetime

import utils.router_constants as c
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import utils.get_link_content as glc
import data.rss_cache as rc

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_feed_item_list():
    soup = glc.get_link_content_with_bs_no_params(c.jandan_page_prefix, c.html_parser)
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
            if link in rc.feed_item_cache.keys():
                # logging.info("getting cache item with key: " + link)
                feed_item = rc.feed_item_cache[link]
            else:
                # logging.info("key: " + link + " not found in the cache.")
                feed_item = do.FeedItem(title=title,
                                        link=link,
                                        author=author,
                                        guid=link,
                                        withContent=False)

            feed_item_list.append(feed_item)

    return feed_item_list


def get_individual_post_content(post_list):
    for post in post_list:
        if post.withContent is False:
            soup = glc.get_link_content_with_bs_no_params(post.link, c.html_parser)
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
            post.created_time = tc.convert_time_with_pattern(created_time, c.jandan_time_convert_pattern, 8)
            description_string = ''
            for paragraph in description_list:
                for p in paragraph.find_all('p'):
                    description_string += str(p)
            post.description = description_string
            post.withContent = True

            rc.feed_item_cache[post.guid] = post


def generate_feed_rss():
    item_list = get_feed_item_list()
    get_individual_post_content(item_list)
    feed = gxml.generate_feed_object(
        title="煎蛋",
        link=c.jandan_page_prefix,
        description="煎蛋 - 地球上没有新鲜事",
        language="zh-cn",
        feed_item_list=item_list
    )

    return feed


def check_if_should_query(jandan_key):
    """
    Limit query to at most 1 time in 10 minutes.
    :return: if service should query now
    """

    # if it's the first query, or the last query happened more than 10 minutes, then query again
    if len(rc.feed_cache) == 0 or jandan_key not in rc.feed_cache.keys() or civ.check_should_query_no_state(
            datetime.timestamp(rc.feed_cache[jandan_key].lastBuildDate),
            c.jandan_query_period
    ):
        return True

    return False


def get_rss_xml_response():
    """
    Entry point of the router.
    Currently currency_name is not used.
    :return: XML feed
    """
    jandan_key = 'jandan/latest'
    should_query_website = check_if_should_query(jandan_key)
    logging.info("Query jandan for this call: " + str(should_query_website))
    if should_query_website is True:
        feed = generate_feed_rss()
        rc.feed_cache[jandan_key] = feed
    else:
        feed = rc.feed_cache[jandan_key]

    response_currency = make_response(feed.rss())
    response_currency.headers.set('Content-Type', 'application/rss+xml')

    return response_currency


if __name__ == '__main__':
    pass
