import logging
from router.router_for_rss_feed import RouterForRssFeed
from router.sony_alpha_rumor.sony_alpha_rumor_router_constants import sar_time_convert_pattern, sar_name
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.time_converter import convert_time_with_pattern
from utils.tools import decompose_div


class SonyAlphaRumorsRouter(RouterForRssFeed):

    def _get_article_content(self, article_metadata, entry):
        logging.info("Router %s fetching Sony Alpha article content link=%s", self.router_path, article_metadata.link)
        soup = get_link_content_with_bs_no_params(entry.link)
        if soup is None:
            logging.warning("Router %s failed to fetch page for %s", self.router_path, article_metadata.link)
            return entry
        soup = soup.find('div',
                         class_="single-blog-content single-content entry wpex-mt-20 wpex-mb-40 wpex-clr")

        if soup is not None:
            entry.created_time = convert_time_with_pattern(article_metadata.created_time, sar_time_convert_pattern)
            entry.author = sar_name
            decompose_div(soup, 'addtoany_share_save_container addtoany_content addtoany_content_bottom')
            decompose_div(soup, 'addtoany_share_save_container addtoany_content addtoany_content_top')

            entry.description = soup
            if not entry.description:
                logging.warning("Router %s extracted empty description for %s", self.router_path, article_metadata.link)
            entry.persist_to_cache(self.router_path)
        else:
            logging.warning("Router %s could not find single-blog-content div for %s", self.router_path, article_metadata.link)
