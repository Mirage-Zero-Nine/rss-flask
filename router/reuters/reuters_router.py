import logging
import html

from flask import make_response
from datetime import datetime

import utils.router_constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import data.rss_cache as rc

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def convert_static_link(source_string):
    # sample source image url:
    # https://s2.reutersmedia.net/resources/r/?m=02&amp;d=20220319&amp;t=2&amp;i=1594752456&amp;w=116&amp;fh=&amp;fw=≪=&amp;pl=&amp;sq=&amp;r=LYNXNPEI2I00E
    # converted to: https://static.reuters.com/resources/r/?m=02&d=20220319&t=2&i=1594752456
    url = c.reuters_static_source_prefix + html.unescape(source_string.split("r/")[1]).split("&w=")[0]
    return url


def get_articles_list():
    json_response = glc.load_json_response(c.reuters_page_link, c.reuters_header)
    feed_item_list = []

    for field in json_response["headlines"]:
        link = c.reuters_article_link_prefix + field["url"].strip()
        description = ""
        if field["mainPicUrl"] != "":
            description = '<img src="%s">' % (convert_static_link(field["mainPicUrl"]))

        if link in rc.feed_item_cache.keys():
            # logging.info("getting cache item with key: " + link)

            feed_item = rc.feed_item_cache[link]
        else:
            # logging.info("key: " + link + " not found in the cache.")

            feed_item = do.FeedItem(
                title=field["headline"],
                link=link,
                author="路透新闻部",
                created_time=tc.convert_millisecond_to_datetime(field["dateMillis"]),
                description=description,
                guid=link,
                with_content=False
            )

        feed_item_list.append(feed_item)

    return feed_item_list


def get_individual_article(feed_item_list):
    for feed_item in feed_item_list:
        if feed_item.with_content is False:
            logging.info("need to retrieve from link: " + feed_item.link)
            soup = glc.get_link_content_with_bs_and_header(feed_item.link, c.html_parser, c.reuters_header)
            description_list = soup.find_all(
                "div",
                {"class": "ArticleBodyWrapper"}
            )
            description = ''
            for item in description_list:
                for paragraph in item.find_all(
                        'p',
                        {"class": "Paragraph-paragraph-2Bgue"}
                ):
                    description += str(paragraph)

            feed_item.description = feed_item.description + description
            feed_item.with_content = True

            rc.feed_item_cache[feed_item.guid] = feed_item


def generate_feed_rss():
    feed_item_list = get_articles_list()
    get_individual_article(feed_item_list)
    feed = gxml.generate_feed_object(
        title="路透中文网 - 实时资讯",
        link=c.reuters_source_link,
        description="路透中文网 - 实时资讯",
        language="zh-cn",
        feed_item_list=feed_item_list
    )
    return feed


def check_if_should_query(reuters_key):
    """
    Limit query to at most 1 time in 10 minutes.
    :return: if service should query now
    """

    # if it's the first query, or the last query happened more than 10 minutes, then query again
    if len(rc.feed_cache) == 0 or reuters_key not in rc.feed_cache.keys() or civ.check_should_query_no_state(
            datetime.timestamp(rc.feed_cache[reuters_key].lastBuildDate),
            c.reuters_query_period
    ):
        return True

    return False


def get_rss_xml_response():
    """
    Entry point of the router.
    Currently currency_name is not used.
    :return: XML feed
    """
    reuters_key = 'reuters/realtime/cn'
    should_query_website = check_if_should_query(reuters_key)
    logging.info("Query reuters for this call: " + str(should_query_website))
    if should_query_website is True:
        feed = generate_feed_rss()
        rc.feed_cache[reuters_key] = feed
    else:
        feed = rc.feed_cache[reuters_key]

    response_currency = make_response(feed.rss())
    response_currency.headers.set('Content-Type', 'application/rss+xml')

    return response_currency


if __name__ == '__main__':
    # generate_feed_rss()
    pass
