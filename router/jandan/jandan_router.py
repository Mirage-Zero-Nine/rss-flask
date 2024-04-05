from datetime import datetime

from router.base_router import BaseRouter
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.router_constants import html_parser
from utils.time_converter import convert_time_with_pattern
from utils.tools import decompose_div, decompose_tag_by_class_name, remove_certain_tag


class JandanRouter(BaseRouter):

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        """
        Override this method for each router.
        :return: list of articles
        """
        soup = get_link_content_with_bs_no_params(self.articles_link, html_parser)
        post_list = soup.find_all(
            "div",
            {"class": "post f list-post"}
        )  # type is bs4.element.ResultSet

        metadata_list = []

        for post in post_list:
            title = post.find('h2').text
            link = post.find('h2').find('a')['href']

            if "日好价" not in title:
                save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                metadata_list.append(Metadata(
                    title=title,
                    link=link,
                    guid=link,
                    json_name=generate_json_name(prefix=save_json_path_prefix, name=link)
                ))

        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        """
        Actual method to retrieve content
        :param article_metadata: metadata of article
        :param entry: object stores all the metadata and the content
        """
        soup = get_link_content_with_bs_no_params(article_metadata.link, html_parser)

        try:
            entry.author = soup.find("div", class_="time_s").find("a", class_="post-author").get_text()
        except AttributeError:
            entry.author = "煎蛋"

        try:
            create_time_string = soup.find("div", class_="time_s").get_text(strip=True).split('@')[-1].strip()
            entry.created_time = convert_time_with_pattern(create_time_string, "%Y.%m.%d , %H:%M", 8)
        except AttributeError:
            entry.created_time = datetime.now()

        content = soup.find('div', class_='post f')
        decompose_div(content, 'shang')
        decompose_div(content, 'social-share')
        decompose_div(content, 'jandan-zan')
        decompose_div(content, 'break')
        decompose_div(content, 'time_s')
        decompose_tag_by_class_name(content, 'span', 'comment-big')
        decompose_tag_by_class_name(content, 'a', 'jandan-zan')
        remove_certain_tag(content, 'script')
        remove_certain_tag(content, 'h1')

        remove_ad = content.find("div", align="center", class_="post f")
        if remove_ad:
            remove_ad.extract()
        remove_css_link = content.find("link", rel="stylesheet")
        if remove_css_link:
            remove_css_link.extract()

        entry.description = content
        entry.save_to_json(self.router_path)