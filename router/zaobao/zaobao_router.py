import requests
import time
import logging

from bs4 import BeautifulSoup
from flask import make_response

import constant.constants as c
import router.zaobao.data_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ

# todo: replace it with Redis, this is a temporary solution
# for now using a timestamp to check refresh time, and limit to at most 15 minutes per query
started_time_zaobao = round(time.time() * 1000)
minutes_in_millisecond_15 = 900000  # 15 minutes in millisecond
should_query_zaobao = None
response = None

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_news_list():
    output_news_list = []
    for x in range(2):  # get 2 pages, each page contains 24 items
        data = requests.get(
            'https://www.zaobao.com.sg/realtime/world?_wrapper_format=html&page=' + str(x),
            headers=c.zaobao_headers
        )
        soup = BeautifulSoup(data.text, 'html.parser')
        news_list = soup.find_all(
            "div",
            {"class": "col col-lg-12"}
        )  # type is bs4.element.ResultSet
        logging.info("Current page: " + str(x) + ", items count: " + str(len(news_list)))
        for news in news_list:
            title = news.find('a').contents[0].text
            news_item = do.FeedItem()
            news_item.title = title
            news_item.link = c.zaobao_story_prefix + news.find('a')['href']
            output_news_list.append(news_item)

    logging.info("Final output length: " + str(len(output_news_list)))
    return output_news_list


def get_individual_news_content(news_list):
    for item in news_list:
        # add to cache to avoid duplication
        soup = get_link_content(item.link)
        post_list = soup.find_all(
            'div',
            {'class': 'article-content-rawhtml'}
        )
        title_list = soup.find_all(
            'h4',
            {'class': 'title-byline byline'}
        )
        time_list = soup.find_all(
            'h4',
            {'class': 'title-byline date-published'}
        )
        news_text = ''
        item.created_time = time_list[0].text.split('/')[1].strip()

        for e in title_list:
            item.author = e.find_all('a')[0].text.strip()
        for post in post_list:

            for text in post.find_all('p'):
                news_text += str(text)
            item.description = news_text
    news_list.sort(
        key=lambda x: tc.convert_time_zaobao(x.created_time),
        reverse=True
    )


def get_link_content(link):
    data = requests.get(link, headers=c.zaobao_headers)
    soup = BeautifulSoup(data.text, 'html.parser')
    return soup


def get_rss_xml():
    global response, started_time_zaobao
    should_query_website = check_if_should_query()
    logging.info(
        "Should query zaobao for this call: " +
        str(should_query_website) +
        ", current start time: " +
        str(started_time_zaobao)
    )
    if should_query_website is True:
        response = generate_news_rss_feed()

    return response


def generate_news_rss_feed():
    global response
    news_list = get_news_list()
    get_individual_news_content(news_list)
    item_list = []

    for i in news_list:
        item = gxml.create_item(
            title=i.title,
            link=i.link,
            description=i.description,
            author=i.author,
            guid=i.link,
            pubDate=tc.convert_time_zaobao(i.created_time),
            isPermaLink=False
        )

        item_list.append(item)

    feed = gxml.generate_feed(
        title="联合早报 - 国际即时新闻",
        link=c.zaobao_realtime_frontpage_prefix,
        description="新加坡、中国、亚洲和国际的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。",
        language="zh-cn",
        items=item_list
    )
    response = make_response(feed)
    response.headers.set('Content-Type', 'application/rss+xml')
    return response


def check_if_should_query():
    """
    Limit query to at most 1 time in 15 minutes.
    Todo: refactor this implementation by using redis to both dedup and limit query speed.
    :return: if service should query now
    """
    global should_query_zaobao
    global started_time_zaobao

    # if it's the first query, or the last query happened more than 15 minutes, then query again
    if civ.check_should_query(should_query_zaobao, started_time_zaobao, minutes_in_millisecond_15):
        should_query_zaobao = False
        started_time_zaobao = round(time.time() * 1000)
        return True

    return False


if __name__ == '__main__':
    # pass

    list = get_news_list()
    get_individual_news_content(list)
    print(list)

    # generate_news_rss_feed()
