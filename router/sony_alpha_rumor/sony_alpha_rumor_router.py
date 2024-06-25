from router.router_for_rss_feed import RouterForRssFeed
from router.sony_alpha_rumor.sony_alpha_rumor_router_constants import sar_time_convert_pattern, sar_name
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.time_converter import convert_time_with_pattern
from utils.tools import decompose_div


class SonyAlphaRumorsRouter(RouterForRssFeed):

    def _get_article_content(self, article_metadata, entry):
        soup = get_link_content_with_bs_no_params(entry.link).find('div',
                                                                   class_="single-blog-content single-content entry wpex-mt-20 wpex-mb-40 wpex-clr")

        if soup is not None:
            entry.created_time = convert_time_with_pattern(article_metadata.created_time, sar_time_convert_pattern)
            entry.author = sar_name
            decompose_div(soup, 'addtoany_share_save_container addtoany_content addtoany_content_bottom')
            decompose_div(soup, 'addtoany_share_save_container addtoany_content addtoany_content_top')

            entry.description = soup
            entry.save_to_json(self.router_path)
