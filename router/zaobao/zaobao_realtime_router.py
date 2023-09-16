import logging

from flask import make_response

from data.feed_item_object import FeedItem
from data.rss_cache import feed_item_cache, feed_cache
from router.zaobao.zaobao_util import feed_title_mapping, region_link_mapping, feed_description_mapping
from utils.cache_utilities import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import get_link_content_with_bs_and_header
from utils.router_constants import zaobao_realtime_page_prefix, zaobao_realtime_page_suffix, html_parser, \
    zaobao_headers, zaobao_query_period, zaobao_story_prefix, zaobao_time_convert_pattern
from utils.time_converter import convert_time_with_pattern

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_news_list(region):
    output_news_list = []
    for x in range(2):  # get 2 pages, each page contains 24 items
        link = zaobao_realtime_page_prefix + region + zaobao_realtime_page_suffix + str(x)
        soup = get_link_content_with_bs_and_header(link,
                                                   html_parser,
                                                   zaobao_headers)
        news_list = soup.find_all(
            "div",
            {"class": "col col-lg-12"}
        )  # type is bs4.element.ResultSet

        for news in news_list:
            title = news.find('a').contents[0].text
            link = zaobao_story_prefix + news.find('a')['href']

            if link in feed_item_cache.keys():
                news_item = feed_item_cache[link]
            else:
                news_item = FeedItem(title=title,
                                     link=link,
                                     guid=link,
                                     with_content=False)
            output_news_list.append(news_item)

    return output_news_list


def get_individual_news_content(news_list):
    for item in news_list:
        if item.with_content is False:

            soup = get_link_content_with_bs_and_header(item.link, html_parser, zaobao_headers)
            post_list = soup.find_all(
                'div',
                {'class': 'article-content-rawhtml'}
            )
            title_list = soup.find_all(
                'h4',
                {'class': 'title-byline byline'}
            )
            time_list = soup.find_all(
                'div',
                {'class': 'story-postdate'}
            )
            news_text = ""
            try:
                image_url = soup.find('meta',
                                      {'property': 'og:image:url'}
                                      )["content"]  # get image url from meta content
                figcaption = soup.find_all("figcaption")[0].text
                image_tag = '<img src="%s" alt="%s">' % (image_url, figcaption)
                news_text = image_tag + figcaption
            except IndexError:
                logging.error("Getting error when trying to extract image from: " + item.link)

            item.created_time = convert_time_with_pattern(time_list[0].text.split('/')[1].strip(),
                                                          zaobao_time_convert_pattern,
                                                          8)
            for e in title_list:
                item.author = e.find_all('a')[0].text.strip()
            for post in post_list:

                for text in post.find_all('p'):
                    news_text += str(text)
                item.description = news_text
            item.with_content = True
            feed_item_cache[item.guid] = item


def generate_news_rss_feed(region):
    feed_item_list = get_news_list(region)
    get_individual_news_content(feed_item_list)
    feed = generate_feed_object(
        title=feed_title_mapping[region],
        link=region_link_mapping[region],
        description=feed_description_mapping[region],
        language="zh-cn",
        feed_item_list=feed_item_list
    )

    return feed


def get_rss_xml_response(region):
    """
    Entry point of the router.
    :return: XML feed
    """

    zaobao_key = "zaobao/" + region
    should_query_website = check_query(zaobao_key, zaobao_query_period, f'Zaobao {region}')

    if should_query_website is True:
        feed = generate_news_rss_feed(region)
        feed_cache[zaobao_key] = feed
    else:
        feed = feed_cache[zaobao_key]

    zaobao_response = make_response(feed.rss())
    zaobao_response.headers.set('Content-Type', 'application/rss+xml')

    return zaobao_response
