import time
import logging

from flask import make_response

import constant.constants as c
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import utils.get_link_content as glc

started_time_zaobao_realtime_world = round(time.time() * 1000)
should_query_zaobao_realtime_world = None
response_zaobao_realtime_world = None

started_time_zaobao_realtime_china = round(time.time() * 1000)
should_query_zaobao_realtime_china = None
response_zaobao_realtime_china = None

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)

region_link_mapping = {
    c.zaobao_region_china: c.zaobao_realtime_china_frontpage_prefix,
    c.zaobao_region_world: c.zaobao_realtime_china_frontpage_prefix
}
feed_description_mapping = {
    c.zaobao_region_china: "中国的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。",
    c.zaobao_region_world: "国际的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。"
}
feed_title_mapping = {
    c.zaobao_region_china: "联合早报 - 中港台即时新闻",
    c.zaobao_region_world: "联合早报 - 国际即时新闻"
}


def get_news_list(region):
    output_news_list = []
    for x in range(2):  # get 2 pages, each page contains 24 items
        link = c.zaobao_realtime_page_prefix + region + c.zaobao_realtime_page_suffix + str(x)
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

        item.created_time = tc.convert_time_with_pattern(time_list[0].text.split('/')[1].strip(),
                                                         c.zaobao_time_convert_pattern,
                                                         8)

        for e in title_list:
            item.author = e.find_all('a')[0].text.strip()
        for post in post_list:

            for text in post.find_all('p'):
                news_text += str(text)
            item.description = news_text
        # logging.debug("Post content: " + item.description)


def generate_news_rss_feed(region):
    feed_item_list = get_news_list(region)
    get_individual_news_content(feed_item_list)
    feed = gxml.generate_rss_by_feed_object(
        title=feed_title_mapping[region],
        link=region_link_mapping[region],
        description=feed_description_mapping[region],
        language="zh-cn",
        feed_item_list=feed_item_list
    )

    return feed


def check_if_should_query(region):
    """
    Limit query to at most 1 time in 15 minutes.
    Todo: refactor this implementation by using redis to both dedup and limit query speed.
    :return: if service should query now
    """
    global should_query_zaobao_realtime_world, started_time_zaobao_realtime_world
    global should_query_zaobao_realtime_china, started_time_zaobao_realtime_china

    # if it's the first query, or the last query happened more than 15 minutes, then query again
    if region == c.zaobao_region_world:
        if civ.check_should_query(should_query_zaobao_realtime_world, started_time_zaobao_realtime_world,
                                  c.zaobao_query_period):
            should_query_zaobao_realtime_world = False
            started_time_zaobao_realtime_world = round(time.time() * 1000)
            return True
    elif region == c.zaobao_region_china:
        if civ.check_should_query(should_query_zaobao_realtime_china, started_time_zaobao_realtime_china,
                                  c.zaobao_query_period):
            should_query_zaobao_realtime_china = False
            started_time_zaobao_realtime_china = round(time.time() * 1000)
            return True
    else:
        raise SyntaxError("Invalid region name for this router: " + region)

    return False


def get_rss_xml_response(region):
    """
    Entry point of the router.
    :return: XML feed
    """
    global response_zaobao_realtime_world, started_time_zaobao_realtime_world
    global response_zaobao_realtime_china, started_time_zaobao_realtime_china

    should_query_website = check_if_should_query(region)
    logging.info(
        "Should query zaobao for this call: " +
        str(should_query_website) +
        ", china start time: " +
        str(started_time_zaobao_realtime_china) +
        ", world start time: " +
        str(started_time_zaobao_realtime_world) +
        ", region: " +
        region
    )
    # Todo: refactor this logic
    if should_query_website is True:
        feed = generate_news_rss_feed(region)
        if region == c.zaobao_region_china:
            response_zaobao_realtime_china = make_response(feed)
            response_zaobao_realtime_china.headers.set('Content-Type', 'application/rss+xml')
            return response_zaobao_realtime_china
        elif region == c.zaobao_region_world:
            response_zaobao_realtime_world = make_response(feed)
            response_zaobao_realtime_world.headers.set('Content-Type', 'application/rss+xml')
            return response_zaobao_realtime_world
        else:
            raise SyntaxError("Invalid region: " + region)
    else:
        if region == c.zaobao_region_china:
            return response_zaobao_realtime_china
        elif region == c.zaobao_region_world:
            return response_zaobao_realtime_world
        else:
            raise SyntaxError("Invalid region: " + region)


if __name__ == '__main__':
    pass
