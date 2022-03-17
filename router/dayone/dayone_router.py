import time
import logging

from flask import make_response

import constant.constants as c
import utils.get_link_content as glc
import router.zaobao.data_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ

started_time_dayone = round(time.time() * 1000)
should_query_dayone = None
response_dayone = None

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
        feed_item = do.FeedItem()
        feed_item.title = title
        feed_item.link = link
        feed_item_list.append(feed_item)

    # print(entry_list)
    return feed_item_list


def get_individual_article(entry_list):
    for entry in entry_list:
        soup = glc.get_link_content_with_bs_no_params(entry.link, c.html_parser)
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
        entry.created_time = split_metadata[0].strip()
        entry.author = split_metadata[1]
        for description in description_list:
            for text in description.find_all('p'):
                description_text += str(text)
        entry.description = description_text


def get_feed(entry_list):
    item_list = []
    for entry in entry_list:
        item = gxml.create_item(
            title=entry.title,
            link=entry.link,
            description=entry.description,
            author=entry.author,
            guid=entry.link,
            pubDate=tc.convert_time_dayone(entry.created_time),
            isPermaLink=False
        )
        item_list.append(item)

    feed = gxml.generate_rss_by_feed_object(
        title="Day One Blog",
        link=c.dayone_blog_link,
        description="Day One Blog - Your Journal for Life | Day One",
        language="en-US",
        items=item_list
    )

    return feed


def check_if_should_query():
    """
    Limit query to at most 1 time in 6 hours.
    Todo: refactor this implementation by using redis to both dedup and limit query speed.
    :return: if service should query now
    """
    global should_query_dayone
    global started_time_dayone

    # if it's the first query, or the last query happened more than 6 hours, then query again
    if civ.check_should_query(should_query_dayone, started_time_dayone, c.dayone_query_period):
        should_query_dayone = False
        started_time_dayone = round(time.time() * 1000)
        return True

    return False


def get_rss_xml_response():
    global response_dayone

    bool_should_query = check_if_should_query()
    logging.info(
        "Should query day one blog for this call: " +
        str(bool_should_query) +
        ", current start time: " +
        str(started_time_dayone)
    )
    if bool_should_query is True:
        entry_list = get_articles_list()
        get_individual_article(entry_list)
        feed = get_feed(entry_list)

        response = make_response(feed)
        response.headers.set('Content-Type', 'application/rss+xml')

    return response_dayone


if __name__ == '__main__':
    get_rss_xml_response()
