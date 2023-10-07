from utils.feed_item_object import Metadata, convert_router_path_to_save_path_prefix, generate_json_name
from router.base_router import BaseRouter
from router.dayone.day_one_blog_constants import day_one_blog_time_convert_pattern
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.router_constants import html_parser
from utils.time_converter import convert_time_with_pattern


class DayOneBlogRouter(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        """
        Override this method for each router.
        :return: list of articles
        """
        metadata_list = []

        soup = get_link_content_with_bs_no_params(self.articles_link, html_parser)
        entry_list = soup.find_all(
            "h3",
            {"class": "entry-title"}
        )

        for entry in entry_list:
            title = entry.find("a").text
            link = entry.find('a')['href']
            if link and title:
                save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                metadata = Metadata(
                    title=title,
                    link=link,
                    json_name=generate_json_name(prefix=save_json_path_prefix, name=link)
                )
                metadata_list.append(metadata)

        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        soup = get_link_content_with_bs_no_params(article_metadata.link, html_parser)
        entry.author = soup.find('meta', attrs={'name': 'author'})['content']

        publish_date = soup.find_all(
            "ul",
            {'class': "entry-meta"}
        )[0].find('li', text=True).get_text(strip=True)
        entry.created_time = convert_time_with_pattern(publish_date, day_one_blog_time_convert_pattern)

        entry_content = soup.find('div', class_='entry-content')

        for element in entry_content.find_all(style=True):
            del element['style']

        noscript_imgs = entry_content.select('noscript img')
        for img in noscript_imgs:
            img.attrs = {'src': img['src']}  # Keep only the 'src' attribute

        figure_tags = entry_content.find_all('figure')

        for figure_tag in figure_tags:
            noscript_img_tag = figure_tag.select_one('noscript img')
            existing_img_tag = figure_tag.find('img')
            if noscript_img_tag and existing_img_tag:
                existing_img_tag.replace_with(noscript_img_tag)
                noscript_tag = figure_tag.find('noscript')
                noscript_tag.extract()

        for p_element in entry_content.find_all('p', class_='is-style-default has-background'):
            p_element.extract()

        for div in entry_content.find_all('div', class_='sharedaddy sd-sharing-enabled'):
            div.extract()

        entry.description = entry_content
        entry.save_to_json(self.router_path)
