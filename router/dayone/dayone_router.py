import logging

from flask import make_response
from datetime import datetime

import constant.constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import data.rss_cache as rc

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list():
    soup = glc.get_link_content_with_bs_no_params(c.dayone_blog_link, c.html_parser)
    feed_item_list = []
    entry_list = soup.find_all(
        "h3",
        {"class": "entry-title"}
    )

    for entry in entry_list:
        title = entry.find("a").text
        link = entry.find('a')['href']

        if link in rc.feed_item_cache.keys():
            # logging.info("getting cache item with key: " + link)
            feed_item_list.append(rc.feed_item_cache[link])
        else:
            # logging.info("key: " + link + " not found in the cache.")
            feed_item = do.FeedItem(title=title,
                                    link=link,
                                    guid=link,
                                    withContent=False)
            feed_item_list.append(feed_item)

    return feed_item_list


def get_individual_article(entry_list):
    for post in entry_list:
        if post.withContent is False:
            soup = glc.get_link_content_with_bs_no_params(post.link, c.html_parser)
            description_list = soup.find_all(
                "div",
                {"class": "entry-content"}
            )
            description_text = ''
            metadata_list = soup.find_all(
                "div",
                {'class': "entry-meta"}
            )
            # sample metadata: December 31, 2020 by The Day One Team
            split_metadata = metadata_list[0].text.split(" by ")
            post.created_time = tc.convert_time_with_pattern(split_metadata[0].strip(),
                                                              c.dayone_time_convert_pattern)
            post.author = split_metadata[1]
            for description in description_list:
                for text in description.find_all('p'):
                    description_text += str(text)
            post.description = description_text
            post.withContent = True

            rc.feed_item_cache[post.guid] = post


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = gxml.generate_feed_object(
        title="Day One Blog",
        link=c.dayone_blog_link,
        description="Day One Blog - Your Journal for Life | Day One",
        language="en-US",
        feed_item_list=entry_list
    )

    return feed


def check_if_should_query(dayone_key):
    """
    Limit query to at most 1 time in 10 minutes.
    :return: if service should query now
    """

    # if it's the first query, or the last query happened more than 10 minutes, then query again
    if len(rc.feed_cache) == 0 or dayone_key not in rc.feed_cache.keys() or civ.check_should_query_no_state(
            datetime.timestamp(rc.feed_cache[dayone_key].lastBuildDate),
            c.dayone_query_period
    ):
        return True

    return False


def get_rss_xml_response():
    """
    Entry point of the router.
    Currently currency_name is not used.
    :return: XML feed
    """
    dayone_key = 'dayone/blog'
    should_query_website = check_if_should_query(dayone_key)
    logging.info("Query Day One Blog for this call: " + str(should_query_website))
    if should_query_website is True:
        feed = generate_feed_rss()
        rc.feed_cache[dayone_key] = feed
    else:
        feed = rc.feed_cache[dayone_key]

    response_currency = make_response(feed.rss())
    response_currency.headers.set('Content-Type', 'application/rss+xml')

    return response_currency


if __name__ == '__main__':
    get_rss_xml_response()
