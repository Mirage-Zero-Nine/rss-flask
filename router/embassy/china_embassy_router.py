import logging

from flask import make_response

from data.feed_item_object import FeedItem
from data.rss_cache import feed_cache, feed_item_cache
from utils.tools import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import get_link_content_with_urllib_request
from utils.router_constants import china_embassy_filter, china_embassy_period, china_embassy_prefix
from utils.time_converter import convert_time_with_pattern

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.INFO)


def get_articles_list():
    soup = get_link_content_with_urllib_request("http://losangeles.china-consulate.org/tzgg/")
    page = soup.find("ul", {"class": "tt"})

    article_list = []
    for item in page:
        article = item.find('a')

        try:
            title = article.text
            link = article['href']
            if article != -1 and china_embassy_filter not in title:
                if link in feed_item_cache.keys():
                    feed_item = feed_item_cache[link]
                else:
                    feed_item = FeedItem(
                        title=title,
                        link=generate_link(link),
                        guid=link,
                        with_content=False,
                        description='',
                        author='中华人民共和国驻洛杉矶总领事馆'
                    )

                article_list.append(feed_item)
        except AttributeError:
            continue

    return article_list


def generate_link(link):
    """
    There are 2 types of the link:
    -
    :param link: link text
    :return: formatted link
    """
    if len(link) > 35:
        return link

    return china_embassy_prefix + link[1:]


def extract_content(entry, link):
    if "http://www.china-embassy.org" in link:
        soup = get_link_content_with_urllib_request(link)

        created_time = soup.find('div', {'class': 'date text-center'}).text
        entry.created_time = convert_time_with_pattern(created_time, '%Y/%m/%d %H:%M', -8)

        paragraph = soup.find_all('p', {'class': 'western'})
        entry.description = paragraph[0].text
    elif 'fmprc.gov.cn' not in link:
        soup = get_link_content_with_urllib_request(link)
        created_time = soup.find('div', {'id': 'News_Body_Time'}).text
        if len(created_time) == 0:
            try:
                text = soup.find('div', {'id': 'News_Body_subitle'}).text.split('：')[1]
                entry.created_time = convert_time_with_pattern(text, '%Y/%m/%d', -8)
            except AttributeError:
                pass
        else:
            entry.created_time = convert_time_with_pattern(created_time, '%Y-%m-%d %H:%M', -8)
        paragraph = soup.find('div', {'id': 'News_Body_Txt_A'})
        for p in paragraph:
            entry.description = entry.description + "<p>" + p.text + "</p>"
        entry.with_content = True
        feed_item_cache[entry.guid] = entry


def get_individual_article(entry_list):
    for entry in entry_list:
        if entry.with_content is False:
            extract_content(entry, entry.link)
            entry.with_content = True


def generate_feed_rss():
    article_list = get_articles_list()
    get_individual_article(article_list)
    feed = generate_feed_object(
        title='中国驻洛杉矶总领事馆 - 通知公告',
        link='http://losangeles.china-consulate.org/tzgg/',
        description='中国驻洛杉矶总领事馆',
        language='zh-cn',
        feed_item_list=article_list
    )

    return feed


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """

    china_embassy_key = "/chinese_embassy"
    should_query_website = check_query(china_embassy_key, china_embassy_period, "Embassy")

    if should_query_website is True:
        feed = generate_feed_rss()
        feed_cache[china_embassy_key] = feed
    else:
        feed = feed_cache[china_embassy_key]

    china_embassy_response = make_response(feed.rss())
    china_embassy_response.headers.set('Content-Type', 'application/rss+xml')

    return china_embassy_response


if __name__ == '__main__':
    generate_feed_rss()
