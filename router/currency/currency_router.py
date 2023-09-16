import logging

from flask import make_response

from data.rss_cache import feed_cache
from router.currency.currency_util import get_page_header, extract_row, item_dedup_and_add_to_list, validate_row
from utils.cache_utilities import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import post_request_with_payload
from utils.router_constants import currency_query_page_count, currency_query_period, currency_link, \
    currency_search_link, html_parser

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)
array = ["货币名称: ", "现汇买入价: ", "现钞买入价: ", "现汇卖出价: ", "现钞卖出价: ", "中行折算价: "]


def generate_feed_rss():
    feed_item_object_list = []
    for i in range(currency_query_page_count):  # query first 10 pages
        page = i + 1
        payload_data = get_page_header(page)
        soup = post_request_with_payload(currency_search_link, html_parser, payload_data)
        exchange_price_list = soup.find_all(
            'table'
        )
        table = exchange_price_list[1]

        # find all rows contain currency price
        rows = table.findChildren(['th', 'tr'])

        for row in rows:
            if validate_row(row) is not None:
                title_text = ""
                item = extract_row(row, title_text)
                item_dedup_and_add_to_list(item, feed_item_object_list)

    # create rss feed object
    feed = generate_feed_object(
        title="中国银行外汇牌价 - 人民币兑美元",
        link=currency_link,
        description="中国银行人民币兑美元牌价",
        language="zh-cn",
        feed_item_list=feed_item_object_list
    )

    return feed


def get_rss_xml_response(currency_name):
    """
    Entry point of the router.
    Currently, currency_name is not used.
    :return: XML feed
    """
    currency_key = 'currency/' + currency_name
    should_query_website = check_query(currency_key, currency_query_period, "currency")
    if should_query_website is True:
        feed = generate_feed_rss()
        feed_cache[currency_key] = feed
    else:
        feed = feed_cache[currency_key]

    response_currency = make_response(feed.rss())
    response_currency.headers.set('Content-Type', 'application/rss+xml')

    return response_currency


if __name__ == '__main__':
    pass
