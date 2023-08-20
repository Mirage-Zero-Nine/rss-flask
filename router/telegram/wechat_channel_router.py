import logging

from flask import make_response
from datetime import datetime

import utils.router_constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import data.rss_cache as fc

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list(link_config):
    soup = glc.get_link_content_with_bs_no_params(link_config[c.telegram_wechat_channel_url])
    all_articles = soup.find_all('div', {'class': 'tgme_widget_message_text'})
    created_time = soup.find_all('time', {'class': 'time'})
    index = 0
    article_list = []
    for item in all_articles:
        title = item.find_all('a')[1].text
        link = item.find_all('a')[1]['href']
        created_time_string = created_time[index].get('datetime')
        if link not in fc.feed_item_cache.keys():
            logging.info(link + " not found in cache.")
            logging.info("Original post created at: " + created_time_string)
            feed_item = do.FeedItem(
                title=title,
                link=link,
                description='笔吧评测室',
                author='',
                guid=link,
                created_time=tc.convert_time_with_pattern(created_time_string, '%Y-%m-%dT%H:%M:%S%z'),
                with_content=False
            )

        else:
            logging.info(link + " was found in cache.")
            feed_item = fc.feed_item_cache.get(link)
            logging.info("Post was created at: " + str(feed_item.created_time))

        index += 1
        article_list.append(feed_item)

    return article_list


def get_individual_article(entry_list):
    for entry in entry_list:
        logging.info("title: " + entry.title)
        logging.info("created at: " + str(entry.created_time))
        if entry.with_content is False:

            soup = glc.get_link_content_with_bs_no_params(entry.link).find('div', class_='rich_media_content')

            # remove all the style in the tags
            for tag in soup.find_all(['p', 'span', 'strong']):
                tag.attrs.pop('style', None)
                tag.attrs.pop('data-vmark', None)

            # only extract image source link and class name for img tag
            for img in soup.find_all('img'):
                if img.has_attr('class'):
                    img_class = img['class']
                    img_data_src = img['data-src']
                    img.attrs = {'class': img_class, 'data-src': img_data_src}

            for paragraph in soup.find_all('p'):
                entry.description += str(paragraph)

            entry.with_content = True
            fc.feed_item_cache[entry.guid] = entry


def generate_feed_rss(link_config):
    entry_list = get_articles_list(link_config)
    get_individual_article(entry_list)
    feed = gxml.generate_feed_object(
        title='微信公众号',
        link=c.telegram_wechat_channel_url,
        description='微信公众号',
        language='zh-cn',
        feed_item_list=entry_list
    )

    return feed


def check_if_should_query(wechat_channel_key):
    """
    Limit query to at most 1 time in 15 minutes.
    :return: if service should query now
    """

    if len(fc.feed_cache) == 0 or wechat_channel_key not in fc.feed_cache.keys() or civ.check_should_query_no_state(
            datetime.timestamp(fc.feed_cache[wechat_channel_key].lastBuildDate),
            c.telegram_wechat_channel_period
    ):
        return True

    return False


def get_rss_xml_response(link_config):
    """
    Entry point of the router.
    :return: XML feed
    """

    telegram_wechat_channel_key = "/telegram/wechat"
    should_query_telegram = check_if_should_query(telegram_wechat_channel_key)
    logging.info(
        "Should query telegram channel for this call: " + str(should_query_telegram)
    )

    if should_query_telegram is True:
        feed = generate_feed_rss(link_config)
        fc.feed_cache[telegram_wechat_channel_key] = feed
    else:
        feed = fc.feed_cache[telegram_wechat_channel_key]

    telegram_wechat_channel_response = make_response(feed.rss())
    telegram_wechat_channel_response.headers.set('Content-Type', 'application/rss+xml')

    return telegram_wechat_channel_response
