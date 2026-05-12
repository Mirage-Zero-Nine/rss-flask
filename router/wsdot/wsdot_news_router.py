import logging

from router.router_for_rss_feed import RouterForRssFeed
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.time_converter import convert_wsdot_news_time


class WsdotNewsRouter(RouterForRssFeed):

    def _get_article_content(self, article_metadata, entry):
        soup = get_link_content_with_bs_no_params(article_metadata.link)
        if soup is None:
            logging.warning("Router %s failed to fetch article content for %s", self.router_path, article_metadata.link)
            return

        post_content = soup.find("div", class_="field field--name-body field--type-text-with-summary field--label-hidden field--item")
        if post_content is None:
            logging.warning("Router %s could not find body field for %s", self.router_path, article_metadata.link)
            return

        entry.description = post_content

        datetime_div = soup.find("div", class_="field--name-field-date")
        if datetime_div:
            time_tag = datetime_div.find("time")
            if time_tag:
                raw_datetime = time_tag.get("datetime")
                if isinstance(raw_datetime, str) and raw_datetime:
                    entry.created_time = convert_wsdot_news_time(raw_datetime, "%Y-%m-%dT%H:%M:%SZ")

        entry.persist_to_cache(self.router_path)
