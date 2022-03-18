import time
import logging
from flask import make_response

import constant.constants as c
import utils.get_link_content as glc
import router.zaobao.data_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ

started_time_currency = round(time.time() * 1000)
should_query_currency = None
response_currency = None
logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def generate_rss_feed():
    soup = glc.post_request_with_payload(c.currency_search_link, c.html_parser, c.currency_usd_payload_data)
    exchange_price_list = soup.find_all(
        'table'
    )
    table = exchange_price_list[1]
    rows = table.findChildren(['th', 'tr'])
    index = 0

    array = ["货币名称: ", "现汇买入价: ", "现钞买入价: ", "现汇卖出价: ", "现钞卖出价: ", "中行折算价: "]
    feed_item_list = []
    title = ''
    for row in rows:
        item = do.FeedItem()
        cells = row.findChildren('td')
        for cell in cells:
            if index == 6:
                index = 0
                item.created_time = cell.text
                continue
            else:
                index += 1
                if index == 1:
                    continue
                else:
                    item.description = item.description + "<p>" + array[index - 1] + cell.text + "</p>"
                    title += array[index - 1] + cell.text + " "
        if item.description != '':
            # logging.info("created time: " + item.created_time.split(" ")[1])
            feed_item = gxml.create_item(
                title=item.description,
                link=c.currency_search_link,
                description=item.description,
                author="中国银行",
                guid=c.currency_search_link,
                pubDate=tc.convert_time_currency(item.created_time.strip()),
                isPermaLink=False
            )
            feed_item_list.append(feed_item)

    feed = gxml.generate_rss_by_feed_object(
        title="中国银行外汇牌价 - 美元",
        link=c.currency_search_link,
        description="中国银行人民币兑美元牌价",
        language="zh-cn",
        items=feed_item_list
    )

    response = make_response(feed)
    response.headers.set('Content-Type', 'application/rss+xml')
    return response


def check_if_should_query():
    """
    Limit query to at most 1 time in 10 minutes.
    :return: if service should query now
    """
    global should_query_currency
    global started_time_currency

    # if it's the first query, or the last query happened more than 10 minutes, then query again
    if civ.check_should_query(should_query_currency, started_time_currency, c.currency_query_period):
        should_query_currency = False
        started_time_currency = round(time.time() * 1000)
        return True

    return False


def get_rss_xml_response(currency_name):
    """
    Entry point of the router.
    :return: XML feed
    """
    global response_currency, started_time_currency
    should_query_website = check_if_should_query()
    logging.info(
        "Should query zaobao for this call: " +
        str(should_query_website) +
        ", current start time: " +
        str(started_time_currency)
    )
    if should_query_website is True:
        response_currency = generate_rss_feed()

    return response_currency


if __name__ == '__main__':
    pass
