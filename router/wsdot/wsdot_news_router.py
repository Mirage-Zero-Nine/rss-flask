import logging
from typing import Optional

from router.base_router import BaseRouter
from router.wsdot.wsdot_news_router_constant import wsdot_blog_blogspot, wsdot_news_prefix
from utils.feed_item_object import Metadata, convert_router_path_to_cache_prefix, generate_cache_key
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.time_converter import convert_wsdot_news_time


class WsdotNewsRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []

        for i in range(0, 3):
            page_url = f"{self.articles_link}?page={i}"
            page_soup = get_link_content_with_bs_no_params(page_url)
            if page_soup is None:
                logging.warning("Router %s failed to fetch page %d of %s", self.router_path, i, page_url)
                continue

            views_row_elements = page_soup.find_all("div", class_="views-field views-field-nothing")
            if not views_row_elements:
                logging.info("Router %s found 0 views-row elements on page %d of %s", self.router_path, i, page_url)

            for views_row in views_row_elements:
                h2_tag = views_row.find("h2")
                if h2_tag is None:
                    logging.info("Router %s skipped views-row with no h2 tag", self.router_path)
                    continue

                a_tag = h2_tag.find("a")
                raw_link: Optional[object] = a_tag.get("href") if a_tag else None
                title = h2_tag.get_text(strip=True)

                if not isinstance(raw_link, str) or not title:
                    logging.info("Router %s skipped views-row: link=%s title=%s", self.router_path, raw_link, title[:50])
                    continue

                link = raw_link

                if link.startswith("/about/news"):
                    link = wsdot_news_prefix + link

                if link.endswith(".htm"):
                    link += "l"

                cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
                metadata = Metadata(title=title, link=link, cache_key=generate_cache_key(prefix=cache_prefix, name=link))
                metadata_list.append(metadata)

        if not metadata_list:
            logging.warning("Router %s extracted 0 articles from wsdot after 3 pages", self.router_path)

        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        soup = get_link_content_with_bs_no_params(article_metadata.link)
        if soup is None:
            logging.warning("Router %s failed to fetch article content for %s", self.router_path, article_metadata.link)
            return

        if article_metadata.link.startswith(wsdot_blog_blogspot):
            self.__extract_wsdot_blog(soup, entry)
        else:
            self.__extract_other_news(soup, entry)

    def __extract_wsdot_blog(self, soup, entry):
        post_content = soup.find("div", class_="post-body entry-content")
        if post_content is None:
            logging.warning("Router %s could not find post-body entry-content for %s", self.router_path, entry.link)
            return
        entry.description = post_content

        date_header_tag = soup.find("h2", class_="date-header")
        if date_header_tag is None or date_header_tag.span is None:
            logging.warning("Router %s could not find date-header span for %s", self.router_path, entry.link)
            return

        date_header = date_header_tag.span.get_text(strip=True)
        if not isinstance(date_header, str) or not date_header:
            logging.warning("Router %s found invalid date-header text for %s", self.router_path, entry.link)
            return

        entry.created_time = convert_wsdot_news_time(date_header, "%A, %B %d, %Y")
        entry.persist_to_cache(self.router_path)

    def __extract_other_news(self, soup, entry):
        post_content = soup.find("div", class_="field field--name-body field--type-text-with-summary field--label-hidden field--item")
        if post_content is None:
            logging.warning("Router %s could not find body field for %s", self.router_path, entry.link)
            return
        entry.description = post_content

        datetime_div = soup.find("div", class_="field--name-field-date")
        if datetime_div is None:
            logging.warning("Router %s could not find field-date for %s", self.router_path, entry.link)
            return

        time_tag = datetime_div.find("time")
        if time_tag is None:
            logging.warning("Router %s could not find time tag for %s", self.router_path, entry.link)
            return

        raw_datetime = time_tag.get("datetime")
        if not isinstance(raw_datetime, str) or not raw_datetime:
            logging.warning("Router %s could not find time tag with datetime attr for %s", self.router_path, entry.link)
            return

        entry.created_time = convert_wsdot_news_time(raw_datetime, "%Y-%m-%dT%H:%M:%SZ")
        entry.persist_to_cache(self.router_path)