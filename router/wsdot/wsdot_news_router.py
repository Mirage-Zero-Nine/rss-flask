import logging

from flask import make_response
from datetime import datetime

import utils.router_constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.check_if_valid as civ
import utils.time_converter as tc
import data.rss_cache as fc


# logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list():
    articles_list = []

    for i in range(0, 3):

        # Find all elements with class "views-row"
        views_row_elements = glc.get_link_content_with_bs_no_params(c.wsdot_news_link + '?page=' + str(i)).find_all(
            class_='views-row')

        # Loop through each views-row element
        for views_row in views_row_elements:

            h2_tags = views_row.find_all('h2')  # Find all <h2> tags within the views-row

            for h2 in h2_tags:
                # Get the href attribute value from the <a> tag
                href = h2.a.get('href')
                title = h2.text

                if href.startswith("/about/news"):
                    href = c.wsdot_news_prefix + href

                if href not in fc.feed_item_cache.keys():
                    logging.info(href + " not found in cache.")
                    feed_item = do.FeedItem(
                        title=title,
                        link=href,
                        description='Washington State Department of Transportation - News',
                        author='WSDOT',
                        guid=href,
                        created_time=None,
                        with_content=False
                    )

                else:
                    logging.info(href + " was found in cache.")
                    feed_item = fc.feed_item_cache.get(href)
                    logging.info("Post was created at: " + str(feed_item.created_time))
                articles_list.append(feed_item)

    return articles_list


def get_individual_article(entry_list):
    for entry in entry_list:
        logging.info("title: " + entry.title)
        logging.info("created at: " + str(entry.created_time))
        if entry.with_content is False:
            if entry.link.startswith(c.wsdotblog_blogspot):
                extract_wsdot_blog(entry)
            else:
                extract_other_news(entry)

            fc.feed_item_cache[entry.guid] = entry


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = gxml.generate_feed_object(
        title='WSDOT - News',
        link=c.wsdot_news_link,
        description='Washington State Department of Transportation - News',
        language='en-us',
        feed_item_list=entry_list
    )

    return feed


def check_if_should_query(wsdot_news_key):
    """
    Limit query to at most 1 time in 15 minutes.
    :return: if service should query now
    """

    if len(fc.feed_cache) == 0 or wsdot_news_key not in fc.feed_cache.keys() or civ.check_should_query_no_state(
            datetime.timestamp(fc.feed_cache[wsdot_news_key].lastBuildDate),
            c.wsdot_news_period
    ):
        return True

    return False


def extract_wsdot_blog(entry):
    soup = glc.get_link_content_with_bs_no_params(entry.link)

    # Find the post content using its class name
    post_content = soup.find('div', class_='post-body entry-content')
    entry.description += str(post_content)
    entry.with_content = True

    date_header = soup.find('h2', class_='date-header').span.text
    entry.created_time = tc.convert_wsdot_news_time(str(date_header), "%A, %B %d, %Y")


def extract_other_news(entry):
    soup = glc.get_link_content_with_bs_no_params(entry.link)

    post_content = soup.find('div',
                             class_='field field--name-body field--type-text-with-summary field--label-hidden field--item')
    entry.description += str(post_content)
    entry.with_content = True

    # Extract the datetime string from the time tag's datetime attribute
    datetime_div = soup.find('div', class_='field--name-field-date')
    datetime_string = datetime_div.find('time')['datetime']
    entry.created_time = tc.convert_wsdot_news_time(str(datetime_string), "%Y-%m-%dT%H:%M:%SZ")


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """

    wsdot_news_key = "/wsdot/news"
    should_query_telegram = check_if_should_query(wsdot_news_key)
    logging.info(
        "Should query WSDOT News for this call: " + str(should_query_telegram)
    )

    if should_query_telegram is True:
        feed = generate_feed_rss()
        fc.feed_cache[wsdot_news_key] = feed
    else:
        feed = fc.feed_cache[wsdot_news_key]

    wsdot_news_response = make_response(feed.rss())
    wsdot_news_response.headers.set('Content-Type', 'application/rss+xml')

    return wsdot_news_response
