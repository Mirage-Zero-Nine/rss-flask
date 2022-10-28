import logging

import utils.time_converter as tc
import data.feed_item_object as do
import data.rss_cache as fc
import utils.router_constants as c

array = ["货币名称: ", "现汇买入价: ", "现钞买入价: ", "现汇卖出价: ", "现钞卖出价: ", "中行折算价: "]
logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def get_page_header(page):
    currency_usd_payload_data = {
        "erectDate": "",
        "nothing": "",
        "pjname": "美元",
        "head": "head_620.js",
        "bottom": "bottom_591.js"
    }

    payload = {
        "erectDate": "",
        "nothing": "",
        "pjname": "美元",
        "page": page,
        "head": "head_620.js",
        "bottom": "bottom_591.js"
    }

    if page == 0:
        return currency_usd_payload_data
    else:
        return payload


def extract_row(row, title_text):
    # each row, exclude first row, is a currency price entry (which will be appended to rss feed object)
    # each row contains 6 columns (cell)
    # each cell has a different price (offshore, onshore, etc.)
    item = do.FeedItem(description='')
    cells = row.findChildren('td')
    index = 0

    for cell in cells:
        if index == 6:
            index = 0
            item.created_time = tc.convert_time_with_pattern(cell.text.strip(),
                                                             c.currency_time_convert_pattern,
                                                             8)
            logging.info("create time: " + str(item.created_time))
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

    item.title = title_text
    item.link = c.currency_link
    item.author = "中国银行"
    item.pubDate = item.created_time
    item.guid = str(item.created_time.date()) + " " + str(item.created_time.hour)

    return item


def item_dedup_and_add_to_list(item, feed_item_object_list):
    """
    Dedup duplicated item by checking dedup key.
    If it's not a duplicated one, add it to output rss feed list.
    :param item: price entry
    :param feed_item_object_list: output rss feed list
    """
    if item.description is not None and item.description != '':

        # dedup key: date and time for this price (round to every 30 minutes)
        # e.g.: 2022-10-20 10:20 will share the same dedup key as 2022-10-20 10:25
        # but 2022-10-20 10:31 will share a different key (minutes rounded by 30)
        dedup_key = str(item.created_time.date()) \
                    + "-" \
                    + str(item.created_time.hour) \
                    + "-" \
                    + str(item.created_time.minute // 30)

        if dedup_key not in fc.feed_item_cache.keys():
            fc.feed_item_cache[dedup_key] = item
            feed_item_object_list.append(item)


def validate_row(row):
    """
    Two cases that makes row invalid:
    1. First row (title row)
    2. Last row (last row only contains CSS)
    :param row:
    :return: return all the cells in current row, or return None if it's a invalid row
    """

    cells = row.findChildren('td')

    if len(cells) > 6:
        return cells
    else:
        return None


if __name__ == '__main__':
    pass
