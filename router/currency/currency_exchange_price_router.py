from router.base_router import BaseRouter
from router.currency.currency_exchange_price_router_constants import currency_exchange_price_query_page_count
from router.currency.currency_exchange_price_util import get_page_header, validate_row, extract_row, \
    item_dedup_and_add_to_list
from utils.get_link_content import post_request_with_payload
from utils.router_constants import html_parser, language_chinese
from utils.xml_utilities import generate_feed_object


class CurrencyExchangePriceRouter(BaseRouter):

    def _generate_feed_rss(self, link_filter=None, title_filter=None):
        feed_item_object_list = []
        for i in range(currency_exchange_price_query_page_count):  # query first 10 pages
            page = i + 1
            payload_data = get_page_header(page)
            soup = post_request_with_payload(self.articles_link, html_parser, payload_data)
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
            title=self.feed_title,
            link=self.original_link,
            description=self.description,
            language=language_chinese,
            feed_item_list=feed_item_object_list
        )

        return feed
