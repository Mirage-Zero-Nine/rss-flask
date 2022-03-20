import time
import logging
from flask import make_response

import constant.constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import router.currency.currency_util as cu

started_time_currency = round(time.time() * 1000)
should_query_currency = None
response_currency = None
logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def generate_feed_rss():
    feed_item_object_list = []
    array = ["货币名称: ", "现汇买入价: ", "现钞买入价: ", "现汇卖出价: ", "现钞卖出价: ", "中行折算价: "]
    created_time_dedup = ''  # remove duplicated price
    for i in range(c.currency_query_page_count):  # query first 6 pages
        page = i + 1
        payload_data = cu.get_page_header(page)
        soup = glc.post_request_with_payload(c.currency_search_link, c.html_parser, payload_data)
        exchange_price_list = soup.find_all(
            'table'
        )
        table = exchange_price_list[1]
        rows = table.findChildren(['th', 'tr'])
        index = 0
        for row in rows:
            title_text = ""
            item = do.FeedItem(description='')
            cells = row.findChildren('td')
            for cell in cells:
                if index == 6:
                    index = 0
                    item.created_time = tc.convert_time_with_pattern(cell.text.strip(),
                                                                     c.currency_time_convert_pattern,
                                                                     8)
                    item.description = "发布时间: " + item.created_time.isoformat() + item.description
                    continue
                else:
                    index += 1
                    if index == 1:
                        continue
                    else:
                        item.description = "<p>" + item.description + array[index - 1] + cell.text.strip() + "</p>"
                        if index == 4:
                            title_text += array[index - 1] + cell.text.strip() + " "
                        # title_text += array[index - 1] + cell.text.strip() + " "

            if item.description is not None and item.description != '' and created_time_dedup != str(item.created_time):
                # logging.info("created time: " + item.created_time.split(" ")[1])
                item.title = title_text
                item.link = c.currency_link
                item.author = "中国银行"
                item.guid = item.created_time
                item.pubDate = item.created_time,
                feed_item_object_list.append(item)
                created_time_dedup = str(item.created_time)

    feed = gxml.generate_rss_by_feed_object(
        title="中国银行外汇牌价 - 人民币兑美元",
        link=c.currency_link,
        description="中国银行人民币兑美元牌价",
        language="zh-cn",
        feed_item_list=feed_item_object_list
    )

    return feed


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
    Currently currency_name is not used.
    :return: XML feed
    """
    global response_currency, started_time_currency
    should_query_website = check_if_should_query()
    logging.info(
        "Query currency price list for this call: " +
        str(should_query_website) +
        ", current start time: " +
        str(started_time_currency)
    )
    if should_query_website is True:
        feed = generate_feed_rss()
        response_currency = make_response(feed)
        response_currency.headers.set('Content-Type', 'application/rss+xml')

    return response_currency


if __name__ == '__main__':
    pass
