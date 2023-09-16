import logging

from flask import make_response

from data.feed_item_object import FeedItem
from data.rss_cache import feed_cache, feed_item_cache
from utils.cache_utilities import check_query
from utils.get_link_content import get_link_content_with_utf8_decode
from utils.router_constants import cnbeta_query_page_count, cnbeta_prefix, cnbeta_period
from utils.time_converter import convert_time_with_pattern
from utils.xml_utilities import generate_feed_object

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list():
    articles_list = []

    for i in range(0, cnbeta_query_page_count):
        link = f"{cnbeta_prefix}/list/latest_{i + 1}.htm"
        soup = get_link_content_with_utf8_decode(link)

        ul_element = soup.find('ul', class_='info_list')
        txt_area_divs = ul_element.find_all('div', class_='txt_area')

        for div in txt_area_divs:
            a_tag = div.find('a')
            href = a_tag.get('href')
            title = a_tag.find('p', class_='txt_detail').text if a_tag.find('p', class_='txt_detail') else None
            link = cnbeta_prefix + href

            if link and title:
                if link in feed_cache.keys():
                    news_item = feed_item_cache[link]
                else:
                    news_item = FeedItem(title=title,
                                         link=link,
                                         guid=link,
                                         with_content=False)
                articles_list.append(news_item)

    return articles_list


def get_individual_article(entry_list):
    for entry in entry_list:
        if entry.with_content is False:
            soup = get_link_content_with_utf8_decode(entry.link)
            time_object = extract_time(soup)
            entry.created_time = convert_time_with_pattern(time_object, '%Y-%m-%d %H:%M:%S', 8)
            entry.description = extract_content(soup)
            entry.author = "cnBeta"
            feed_item_cache[entry.guid] = entry


def extract_time(soup):
    time_element = soup.find('time', class_='time')
    return time_element.get_text() if time_element else None


def extract_content(soup):
    article_cont_div = soup.find('div', class_='articleCont')

    return article_cont_div.decode_contents() if article_cont_div else None


def generate_feed_rss():
    entry_list = get_articles_list()
    get_individual_article(entry_list)
    feed = generate_feed_object(
        title='cnBeta - News',
        link=cnbeta_prefix,
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
    should_query_cnbeta = check_query(cnbeta_key, cnbeta_period, 'cnBeta')

    if should_query_cnbeta is True:
        feed = generate_feed_rss()
        feed_cache[cnbeta_key] = feed
    else:
        feed = feed_cache[cnbeta_key]

    cnbeta_response = make_response(feed.rss())
    cnbeta_response.headers.set('Content-Type', 'application/rss+xml')

    return cnbeta_response
