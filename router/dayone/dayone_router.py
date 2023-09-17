import logging

from flask import make_response

from data.feed_item_object import FeedItem
from data.rss_cache import feed_item_cache, feed_cache
from utils.cache_utilities import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.router_constants import dayone_query_period, html_parser, dayone_blog_link, dayone_time_convert_pattern
from utils.time_converter import convert_time_with_pattern

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.INFO)


def get_articles_list():
    soup = get_link_content_with_bs_no_params(dayone_blog_link, html_parser)
    feed_item_list = []
    entry_list = soup.find_all(
        "h3",
        {"class": "entry-title"}
    )

    for entry in entry_list:
        title = entry.find("a").text
        link = entry.find('a')['href']

        if link in feed_item_cache.keys():
            feed_item_list.append(feed_item_cache[link])
        else:
            feed_item = FeedItem(title=title,
                                 link=link,
                                 guid=link,
                                 with_content=False)
            feed_item_list.append(feed_item)

    return feed_item_list


def get_individual_article(entry_list):
    for post in entry_list:
        if post.with_content is False:
            soup = get_link_content_with_bs_no_params(post.link, html_parser)
            description_list = soup.find_all(
                "div",
                {"class": "entry-content"}
            )

            description_text = ''

            publish_date = soup.find_all(
                "ul",
                {'class': "entry-meta"}
            )[0].find('li', text=True).get_text(strip=True)

            # sample date: August 17, 2023
            post.created_time = convert_time_with_pattern(publish_date, dayone_time_convert_pattern)
            post.author = soup.find('meta', attrs={'name': 'author'})['content']

            for description in description_list:
                for text in description.find_all('p'):
                    description_text += str(text)
            post.description = description_text
            post.with_content = True

            feed_item_cache[post.guid] = post


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = generate_feed_object(
        title="Day One Blog",
        link=dayone_blog_link,
        description="Day One Blog - Your Journal for Life | Day One",
        language="en-US",
        feed_item_list=entry_list
    )

    return feed


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """
    dayone_key = 'dayone/blog'
    should_query_website = check_query(dayone_key, dayone_query_period, "day one")
    if should_query_website is True:
        feed = generate_feed_rss()
        feed_cache[dayone_key] = feed
    else:
        feed = feed_cache[dayone_key]

    response_dayone = make_response(feed.rss())
    response_dayone.headers.set('Content-Type', 'application/rss+xml')

    return response_dayone
