import time
import logging
import html

from flask import make_response

import constant.constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ

started_time_reuters = round(time.time() * 1000)
should_query_reuters = None
response_reuters = None

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

        feed_item = do.FeedItem(
            title=field["headline"],
            link=link,
            author="路透新闻部",
            created_time=tc.convert_millisecond_to_datetime(field["dateMillis"]),
            description=description,
            guid=link
        )

        feed_item_list.append(feed_item)

    return feed_item_list


def get_individual_article(feed_item_list):
    for feed_item in feed_item_list:

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


def generate_feed_rss():
    feed_item_list = get_articles_list()
    get_individual_article(feed_item_list)
    feed = gxml.generate_rss_by_feed_object(
        title="路透中文网 - 实时资讯",
        link=c.reuters_source_link,
        description="路透中文网 - 实时资讯",
        language="zh-cn",
        feed_item_list=feed_item_list
    )
    return feed


def check_if_should_query():
    """
    Limit query to at most 1 time in 6 hours.
    :return: if service should query now
    """
    global should_query_reuters
    global started_time_reuters

    # if it's the first query, or the last query happened more than 6 hours, then query again
    if civ.check_should_query(should_query_reuters, started_time_reuters, c.reuters_query_period):
        should_query_reuters = False
        started_time_reuters = round(time.time() * 1000)
        return True

    return False


def get_rss_xml_response():
    global response_reuters

    bool_should_query = check_if_should_query()
    logging.info(
        "Query router cn website: " +
        str(bool_should_query) +
        ", current start time: " +
        str(started_time_reuters)
    )
    if bool_should_query is True:
        feed = generate_feed_rss()
        response_reuters = make_response(feed)
        response_reuters.headers.set('Content-Type', 'application/rss+xml')

    return response_reuters


if __name__ == '__main__':
    # generate_feed_rss()
    pass
