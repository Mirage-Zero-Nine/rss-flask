from datetime import datetime

from router.base_router import BaseRouter
from router.zhihu.zhihu_daily_router_constants import zhihu_filter, zhihu_daily_link
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix
from utils.get_link_content import get_content_with_utf8_decode_and_disable_verification


class ZhihuDailyRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []
        soup = get_content_with_utf8_decode_and_disable_verification(self.articles_link)
        content_list = soup.find_all(
            "a",
            {"class": "link-button"}
        )

        for item in content_list:
            title = item.find('span').text
            if zhihu_filter in title:
                link = item['href']
                if title and link:
                    save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                    metadata_list.append(
                        Metadata(title=title,
                                 link=zhihu_daily_link + link,
                                 json_name=generate_json_name(prefix=save_json_path_prefix, name=link)))

        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        soup = get_content_with_utf8_decode_and_disable_verification(entry.link)
        content = soup.find(
            "div",
            {"class": "content-inner"}
        )
        entry.description = content
        entry.created_time = datetime.today()
        entry.save_to_json(self.router_path)
