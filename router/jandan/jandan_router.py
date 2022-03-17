import time
import logging

from flask import make_response

import constant.constants as c
import router.zaobao.data_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import utils.get_link_content as glc

started_time_jandan = round(time.time() * 1000)
should_query_jandan = None
response_jandan = None
logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_feed_item_list():
    soup = glc.get_link_content_with_bs_no_params(c.jandan_page_prefix, c.html_parser)
    # print(str(soup))
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
        if "每日好价" not in title:
            item = do.FeedItem()
            item.title = title
            item.link = link
            item.author = author
            feed_item_list.append(item)

    return feed_item_list


def get_individual_post_content(post_list):
    for item in post_list:
        soup = glc.get_link_content_with_bs_no_params(item.link, c.html_parser)
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
        item.created_time = created_time
        description_string = ''
        for paragraph in description_list:
            for p in paragraph.find_all('p'):
                description_string += str(p)
        item.description = description_string


def create_feed(post_list):
    item_list = []

    for i in post_list:
        item = gxml.create_item(
            title=i.title,
            link=i.link,
            description=i.description,
            author=i.author,
            guid=i.link,
            pubDate=tc.convert_time_jandan(i.created_time),
            isPermaLink=False
        )

        item_list.append(item)

    feed = gxml.generate_rss_by_feed_object(
        title="煎蛋",
        link=c.jandan_page_prefix,
        description="煎蛋 - 地球上没有新鲜事",
        language="zh-cn",
        items=item_list
    )

    return feed


def check_if_should_query():
    """
    Limit query to at most 1 time in 2 hours.
    Todo: refactor this implementation by using redis to both dedup and limit query speed.
    :return: if service should query now
    """
    global should_query_jandan
    global started_time_jandan

    # if it's the first query, or the last query happened more than 90 minutes, then query again
    if civ.check_should_query(should_query_jandan, started_time_jandan, c.jandan_query_period):
        should_query_jandan = False
        started_time_jandan = round(time.time() * 1000)
        return True

    return False


def get_jandan_rss_xml():
    item_list = get_feed_item_list()
    get_individual_post_content(item_list)
    feed_rss = create_feed(item_list)
    response = make_response(feed_rss)
    response.headers.set('Content-Type', 'application/rss+xml')
    return response


def get_jandan_rss_xml_response():
    global response_jandan, started_time_jandan
    should_query_website = check_if_should_query()
    logging.info(
        "Should query jandan for this call: " +
        str(should_query_website) +
        ", current start time: " +
        str(started_time_jandan)
    )

    if should_query_website is True:
        response_jandan = get_jandan_rss_xml()

    return response_jandan


if __name__ == '__main__':
    get_jandan_rss_xml()
