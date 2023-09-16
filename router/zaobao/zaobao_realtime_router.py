import logging

from flask import make_response

import utils.router_constants
import data.feed_item_object
import utils.generate_xml
import utils.time_converter
import utils.get_link_content
import data.rss_cache
from utils.cache_utilities import check_query

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)

region_link_mapping = {
    utils.router_constants.zaobao_region_china: utils.router_constants.zaobao_realtime_china_frontpage_prefix,
    utils.router_constants.zaobao_region_world: utils.router_constants.zaobao_realtime_world_frontpage_prefix
}
feed_description_mapping = {
    utils.router_constants.zaobao_region_china: "中国的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。",
    utils.router_constants.zaobao_region_world: "国际的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。"
}
feed_title_mapping = {
    utils.router_constants.zaobao_region_china: "联合早报 - 中港台即时新闻",
    utils.router_constants.zaobao_region_world: "联合早报 - 国际即时新闻"
}


def get_news_list(region):
    output_news_list = []
    for x in range(2):  # get 2 pages, each page contains 24 items
        link = utils.router_constants.zaobao_realtime_page_prefix + region + utils.router_constants.zaobao_realtime_page_suffix + str(x)
        soup = utils.get_link_content.get_link_content_with_bs_and_header(link,
                                                                          utils.router_constants.html_parser,
                                                                          utils.router_constants.zaobao_headers)
        news_list = soup.find_all(
            "div",
            {"class": "col col-lg-12"}
        )  # type is bs4.element.ResultSet
        # logging.info("Current page: " + str(x) + ", items count: " + str(len(news_list)))
        for news in news_list:
            title = news.find('a').contents[0].text
            link = utils.router_constants.zaobao_story_prefix + news.find('a')['href']

            if link in data.rss_cache.feed_item_cache.keys():
                # logging.info("getting cache item with key: " + link)
                news_item = data.rss_cache.feed_item_cache[link]
            else:
                # logging.info("key: " + link + " not found in the cache.")
                news_item = data.feed_item_object.FeedItem(title=title,
                                                           link=link,
                                                           guid=link,
                                                           with_content=False)
            output_news_list.append(news_item)

    logging.info("Final output length: " + str(len(output_news_list)))
    return output_news_list


def get_individual_news_content(news_list):
    for item in news_list:
        # logging.info("Getting content from: " + item.link)
        if item.with_content is False:

            soup = utils.get_link_content.get_link_content_with_bs_and_header(item.link,
                                                                              utils.router_constants.html_parser,
                                                                              utils.router_constants.zaobao_headers)
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

            logging.info("time_list: " + str(time_list))

            item.created_time = utils.time_converter.convert_time_with_pattern(time_list[0].text.split('/')[1].strip(),
                                                                               utils.router_constants.zaobao_time_convert_pattern,
                                                                               8)
            for e in title_list:
                item.author = e.find_all('a')[0].text.strip()
            for post in post_list:

                for text in post.find_all('p'):
                    news_text += str(text)
                item.description = news_text
            item.with_content = True
            data.rss_cache.feed_item_cache[item.guid] = item


def generate_news_rss_feed(region):
    feed_item_list = get_news_list(region)
    get_individual_news_content(feed_item_list)
    feed = utils.generate_xml.generate_feed_object(
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
    should_query_website = check_query(zaobao_key, utils.router_constants.zaobao_query_period, 'Zaobao')

    if should_query_website is True:
        feed = generate_news_rss_feed(region)
        data.rss_cache.feed_cache[zaobao_key] = feed
    else:
        feed = data.rss_cache.feed_cache[zaobao_key]

    zaobao_response = make_response(feed.rss())
    zaobao_response.headers.set('Content-Type', 'application/rss+xml')

    return zaobao_response


if __name__ == '__main__':
    pass
