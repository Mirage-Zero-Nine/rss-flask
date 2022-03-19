import time
import logging

from flask import make_response

import constant.constants as c
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import utils.get_link_content as glc

# todo: replace it with Redis, this is a temporary solution
started_time_zaobao = round(time.time() * 1000)
should_query_zaobao = None
response_zaobao = None

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_news_list():
    output_news_list = []
    for x in range(2):  # get 2 pages, each page contains 24 items
        link = c.zaobao_page_prefix + str(x)
        soup = glc.get_link_content_with_bs_and_header(link, c.html_parser, c.zaobao_headers)
        news_list = soup.find_all(
            "div",
            {"class": "col col-lg-12"}
        )  # type is bs4.element.ResultSet
        logging.info("Current page: " + str(x) + ", items count: " + str(len(news_list)))
        for news in news_list:
            title = news.find('a').contents[0].text
            link = c.zaobao_story_prefix + news.find('a')['href']
            news_item = do.FeedItem(title=title,
                                    link=link,
                                    guid=link)
            output_news_list.append(news_item)

    logging.info("Final output length: " + str(len(output_news_list)))
    return output_news_list


def get_individual_news_content(news_list):
    for item in news_list:
        # logging.info("Getting content from: " + item.link)
        soup = glc.get_link_content_with_bs_and_header(item.link, c.html_parser, c.zaobao_headers)
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

        item.created_time = tc.convert_time_zaobao(time_list[0].text.split('/')[1].strip())

        for e in title_list:
            item.author = e.find_all('a')[0].text.strip()
        for post in post_list:

            for text in post.find_all('p'):
                news_text += str(text)
            item.description = news_text
        # logging.debug("Post content: " + item.description)


def generate_news_rss_feed():
    feed_item_list = get_news_list()
    get_individual_news_content(feed_item_list)
    feed = gxml.generate_rss_by_feed_object(
        title="联合早报 - 国际即时新闻",
        link=c.zaobao_realtime_frontpage_prefix,
        description="国际的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。",
        language="zh-cn",
        feed_item_list=feed_item_list
    )

    return feed


def check_if_should_query():
    """
    Limit query to at most 1 time in 15 minutes.
    Todo: refactor this implementation by using redis to both dedup and limit query speed.
    :return: if service should query now
    """
    global should_query_zaobao
    global started_time_zaobao

    # if it's the first query, or the last query happened more than 15 minutes, then query again
    if civ.check_should_query(should_query_zaobao, started_time_zaobao, c.zaobao_query_period):
        should_query_zaobao = False
        started_time_zaobao = round(time.time() * 1000)
        return True

    return False


def get_rss_xml_response():
    """
    Entry point of the router.
    :return: XML feed
    """
    global response_zaobao, started_time_zaobao
    should_query_website = check_if_should_query()
    logging.info(
        "Should query zaobao for this call: " +
        str(should_query_website) +
        ", current start time: " +
        str(started_time_zaobao)
    )
    if should_query_website is True:
        feed = generate_news_rss_feed()
        response_zaobao = make_response(feed)
        response_zaobao.headers.set('Content-Type', 'application/rss+xml')

    return response_zaobao


if __name__ == '__main__':
    pass
