import logging

from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix
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
                cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
                metadata = Metadata(
                    title=title,
                    link=link,
                    cache_key=generate_cache_key(prefix=cache_prefix, name=link)
                )
                metadata_list.append(metadata)

        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        soup = get_link_content_with_bs_no_params(article_metadata.link, html_parser)
        author_meta = soup.find('meta', attrs={'name': 'author'})
        if author_meta and author_meta.get('content'):
            entry.author = author_meta['content']
        else:
            logging.warning("No author metadata found for: " + article_metadata.link)

        metadata = soup.find_all(
            "ul",
            {'class': "entry-meta"}
        )
        if metadata:
            publish_item = metadata[0].find('li', text=True)
            if publish_item:
                publish_date = publish_item.get_text(strip=True)
                entry.created_time = convert_time_with_pattern(publish_date, day_one_blog_time_convert_pattern)
            else:
                logging.warning("No publish date item found for: " + article_metadata.link)
        else:
            logging.warning("No publish date found for: " + article_metadata.link)
        entry_content = soup.find('div', class_='entry-content')
        if entry_content is None:
            logging.warning("No entry content found for: " + article_metadata.link)
            return entry

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
        entry.persist_to_cache(self.router_path)
