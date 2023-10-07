import logging

from flask import make_response

from utils.feed_item_object import FeedItem
from utils.rss_cache import feed_cache, feed_item_cache
from utils.tools import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.router_constants import wsdot_news_period, wsdot_news_link, wsdot_news_prefix, wsdotblog_blogspot
from utils.time_converter import convert_wsdot_news_time

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.INFO)


def get_articles_list():
    articles_list = []

    for i in range(0, 3):

        # Find all elements with class "views-row"
        views_row_elements = get_link_content_with_bs_no_params(wsdot_news_link + '?page=' + str(i)).find_all(
            class_='views-row')

        # Loop through each views-row element
        for views_row in views_row_elements:

            h2_tags = views_row.find_all('h2')  # Find all <h2> tags within the views-row

            for h2 in h2_tags:
                # Get the href attribute value from the <a> tag
                href = h2.a.get('href')
                title = h2.text

                if href.startswith("/about/news"):
                    href = wsdot_news_prefix + href

                if href not in feed_item_cache.keys():
                    feed_item = FeedItem(
                        title=title,
                        link=href,
                        description='Washington State Department of Transportation - News',
                        author='WSDOT',
                        guid=href,
                        created_time=None,
                        with_content=False
                    )

                else:
                    feed_item = feed_item_cache.get(href)
                articles_list.append(feed_item)

    return articles_list


def get_individual_article(entry_list):
    for entry in entry_list:
        if entry.with_content is False:
            if entry.link.startswith(wsdotblog_blogspot):
                extract_wsdot_blog(entry)
            else:
                extract_other_news(entry)

            feed_item_cache[entry.guid] = entry


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = generate_feed_object(
        title='WSDOT - News',
        link=wsdot_news_link,
        description='Washington State Department of Transportation - News',
        language='en-us',
        feed_item_list=entry_list
    )

    return feed


def extract_wsdot_blog(entry):
    soup = get_link_content_with_bs_no_params(entry.link)

    # Find the post content using its class name
    post_content = soup.find('div', class_='post-body entry-content')
    entry.description += str(post_content)
    entry.with_content = True

    date_header = soup.find('h2', class_='date-header').span.text
    entry.created_time = convert_wsdot_news_time(str(date_header), "%A, %B %d, %Y")


def extract_other_news(entry):
    soup = get_link_content_with_bs_no_params(entry.link)

    post_content = soup.find('div',
                             class_='field field--name-body field--type-text-with-summary field--label-hidden field--item')
    entry.description += str(post_content)
    entry.with_content = True

    # Extract the datetime string from the time tag's datetime attribute
    datetime_div = soup.find('div', class_='field--name-field-date')
    datetime_string = datetime_div.find('time')['datetime']
    entry.created_time = convert_wsdot_news_time(str(datetime_string), "%Y-%m-%dT%H:%M:%SZ")


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """

    wsdot_news_key = "/wsdot/news"
    should_query_the_verge = check_query(wsdot_news_key, wsdot_news_period, "WSDOT")

    if should_query_the_verge is True:
        feed = generate_feed_rss()
        feed_cache[wsdot_news_key] = feed
    else:
        feed = feed_cache[wsdot_news_key]

    wsdot_news_response = make_response(feed.rss())
    wsdot_news_response.headers.set('Content-Type', 'application/rss+xml')

    return wsdot_news_response
