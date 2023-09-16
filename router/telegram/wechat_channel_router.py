import logging

from flask import make_response

from data.feed_item_object import FeedItem
from data.rss_cache import feed_item_cache, feed_cache
from utils.cache_utilities import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.router_constants import telegram_wechat_channel_url, telegram_wechat_channel_period
from utils.time_converter import convert_time_with_pattern

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_articles_list(link_config):
    soup = get_link_content_with_bs_no_params(link_config[telegram_wechat_channel_url])
    all_articles = soup.find_all('div', {'class': 'tgme_widget_message_text'})
    created_time = soup.find_all('time', {'class': 'time'})
    index = 0
    article_list = []
    for item in all_articles:
        if item.find_all('a'):
            title = item.find_all('a')[1].text
            link = item.find_all('a')[1]['href']
            created_time_string = created_time[index].get('datetime')
            if link not in feed_item_cache.keys():
                feed_item = FeedItem(
                    title=title,
                    link=link,
                    description='笔吧评测室',
                    author='',
                    guid=link,
                    created_time=convert_time_with_pattern(created_time_string, '%Y-%m-%dT%H:%M:%S%z'),
                    with_content=False
                )

            else:
                feed_item = feed_item_cache.get(link)

            index += 1
            article_list.append(feed_item)

    return article_list


def get_individual_article(entry_list):
    for entry in entry_list:
        if entry.with_content is False:

            soup = get_link_content_with_bs_no_params(entry.link).find('div',
                                                                       class_='rich_media_content')

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
            feed_item_cache[entry.guid] = entry


def generate_feed_rss(link_config):
    entry_list = get_articles_list(link_config)
    get_individual_article(entry_list)
    feed = generate_feed_object(
        title='微信公众号',
        link=telegram_wechat_channel_url,
        description='微信公众号',
        language='zh-cn',
        feed_item_list=entry_list
    )

    return feed


def get_rss_xml_response(link_config):
    """
    Entry point of the router.
    :return: XML feed
    """

    telegram_wechat_channel_key = "/telegram/wechat"
    should_query_telegram = check_query(telegram_wechat_channel_key,
                                        telegram_wechat_channel_period,
                                        'Telegram Channel')

    if should_query_telegram is True:
        feed = generate_feed_rss(link_config)
        feed_cache[telegram_wechat_channel_key] = feed
    else:
        feed = feed_cache[telegram_wechat_channel_key]

    telegram_wechat_channel_response = make_response(feed.rss())
    telegram_wechat_channel_response.headers.set('Content-Type', 'application/rss+xml')

    return telegram_wechat_channel_response
