import logging

from flask import make_response
from datetime import datetime

from data.feed_item_object import FeedItem
from data.rss_cache import feed_item_cache, feed_cache
from utils.cache_utilities import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import get_link_content_with_bs_and_header, get_link_content_with_urllib_request
from utils.router_constants import zhihu_story_prefix, zhihu_query_period, zhihu_filter, html_parser, zhihu_header

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list():
    soup = get_link_content_with_bs_and_header("https://daily.zhihu.com/",
                                               html_parser,
                                               zhihu_header)
    content_list = soup.find_all(
        "a",
        {"class": "link-button"}
    )
    article_list = []
    for item in content_list:
        title = item.find('span').text
        if zhihu_filter in title:
            link = item['href']

            if link in feed_item_cache.keys():
                feed_item = feed_item_cache[link]
            else:
                feed_item = FeedItem(
                    title=title,
                    link=zhihu_story_prefix + link,
                    with_content=False,
                    guid=link
                )
            article_list.append(feed_item)

    return article_list


def get_individual_article(entry_list):
    for entry in entry_list:
        if entry.with_content is False:
            soup = get_link_content_with_urllib_request(entry.link)
            item_list = soup.find_all(
                "div",
                {"class": "content-inner"}
            )
            entry.description = item_list[0]
            entry.with_content = True
            entry.created_time = datetime.today()

            feed_item_cache[entry.guid] = entry


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = generate_feed_object(
        title="知乎日报",
        link=zhihu_story_prefix,
        description="每日提供高质量新闻资讯",
        language="zh-cn",
        feed_item_list=entry_list
    )

    return feed


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """

    zhihu_key = "zhihu/"
    should_query_website = check_query(zhihu_key, zhihu_query_period, "zhihu")

    if should_query_website is True:
        feed = generate_feed_rss()
        feed_cache[zhihu_key] = feed
    else:
        feed = feed_cache[zhihu_key]

    zhihu_response = make_response(feed.rss())
    zhihu_response.headers.set('Content-Type', 'application/rss+xml')

    return zhihu_response


if __name__ == '__main__':
    generate_feed_rss()
