import logging

from flask import make_response

import utils.router_constants
import utils.get_link_content
import data.feed_item_object
import utils.generate_xml
import data.rss_cache
from utils.cache_utilities import check_query
from utils.time_converter import convert_time_with_pattern

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list():
    articles_list = []

    for i in range(0, utils.router_constants.cnbeta_query_page_count):
        link = f"{utils.router_constants.cnbeta_prefix}/list/latest_{i + 1}.htm"
        soup = utils.get_link_content.get_link_content_with_utf8_decode(link)

        ul_element = soup.find('ul', class_='info_list')
        txt_area_divs = ul_element.find_all('div', class_='txt_area')

        for div in txt_area_divs:
            a_tag = div.find('a')
            href = a_tag.get('href')
            title = a_tag.find('p', class_='txt_detail').text if a_tag.find('p', class_='txt_detail') else None
            link = utils.router_constants.cnbeta_prefix + href

            # Print the results (or do something else with them)
            if link and title:
                if link in data.rss_cache.feed_cache.keys():
                    news_item = data.rss_cache.feed_item_cache[link]
                else:
                    news_item = data.feed_item_object.FeedItem(title=title,
                                                               link=link,
                                                               guid=link,
                                                               with_content=False)
                articles_list.append(news_item)

    return articles_list


def get_individual_article(entry_list):
    for entry in entry_list:
        if entry.with_content is False:
            soup = utils.get_link_content.get_link_content_with_utf8_decode(entry.link)
            time_object = extract_time(soup)
            entry.created_time = convert_time_with_pattern(time_object, '%Y-%m-%d %H:%M:%S', 8)
            entry.description = extract_content(soup)
            entry.author = "cnBeta"
            data.rss_cache.feed_item_cache[entry.guid] = entry


def extract_time(soup):
    time_element = soup.find('time', class_='time')
    return time_element.get_text() if time_element else None


def extract_content(soup):
    article_cont_div = soup.find('div', class_='articleCont')

    return article_cont_div.decode_contents() if article_cont_div else None


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = utils.generate_xml.generate_feed_object(
        title='cnBeta - News',
        link=utils.router_constants.wsdot_news_link,
        description='cnBeta.COM - 中文业界资讯站',
        language='zh-cn',
        feed_item_list=entry_list
    )

    return feed


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """

    cnbeta_key = "cnbeta/news"
    should_query_cnbeta = check_query(cnbeta_key, utils.router_constants.cnbeta_period, 'cnBeta')

    if should_query_cnbeta is True:
        feed = generate_feed_rss()
        data.rss_cache.feed_cache[cnbeta_key] = feed
    else:
        feed = data.rss_cache.feed_cache[cnbeta_key]

    cnbeta_response = make_response(feed.rss())
    cnbeta_response.headers.set('Content-Type', 'application/rss+xml')

    return cnbeta_response
