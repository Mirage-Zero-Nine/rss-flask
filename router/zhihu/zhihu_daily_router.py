import logging

from flask import make_response
from datetime import datetime

import constant.constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.check_if_valid as civ
import data.rss_cache as fc

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list():
    soup = glc.get_link_content_with_bs_and_header("https://daily.zhihu.com/", c.html_parser, c.zhihu_header)
    content_list = soup.find_all(
        "a",
        {"class": "link-button"}
    )
    article_list = []
    for item in content_list:
        title = item.find('span').text
        if c.zhihu_filter in title:
            link = item['href']

            if link in fc.feed_item_cache.keys():
                feed_item = fc.feed_item_cache[link]
            else:
                feed_item = do.FeedItem(
                    title=title,
                    link=c.zhihu_story_prefix + link,
                    withContent=False,
                    guid=link
                )
            article_list.append(feed_item)

    return article_list


def get_individual_article(entry_list):
    for entry in entry_list:
        if entry.withContent is False:
            soup = glc.get_link_content_with_urllib_request(entry.link)
            item_list = soup.find_all(
                "div",
                {"class": "content-inner"}
            )
            entry.description = item_list[0]
            entry.withContent = True
            entry.created_time = datetime.today()

            fc.feed_item_cache[entry.guid] = entry


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = gxml.generate_feed_object(
        title="知乎日报",
        link=c.zhihu_story_prefix,
        description="每日提供高质量新闻资讯",
        language="zh-cn",
        feed_item_list=entry_list
    )

    return feed


def check_if_should_query(zhihu_key):
    """
    Limit query to at most 1 time in 15 minutes.
    :return: if service should query now
    """

    if len(fc.feed_cache) == 0 or zhihu_key not in fc.feed_cache.keys() or civ.check_should_query_no_state(
            datetime.timestamp(fc.feed_cache[zhihu_key].lastBuildDate),
            c.zhihu_query_period
    ):
        return True

    return False


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """

    zhihu_key = "zhihu/"
    should_query_website = check_if_should_query(zhihu_key)
    logging.info(
        "Should query zhihu daily for this call: " + str(should_query_website)
    )

    if should_query_website is True:
        feed = generate_feed_rss()
        fc.feed_cache[zhihu_key] = feed
    else:
        feed = fc.feed_cache[zhihu_key]
    #
    zhihu_response = make_response(feed.rss())
    zhihu_response.headers.set('Content-Type', 'application/rss+xml')
    #
    return zhihu_response


if __name__ == '__main__':
    generate_feed_rss()
