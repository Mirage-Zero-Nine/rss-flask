from router.meta_blog.meta_tech_blog_router_constants import meta_ai_blog_prefix, meta_blog_prefix, meta_blog_link
from router.router_for_rss_feed import RouterForRssFeed
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.time_converter import convert_time_with_pattern
from utils.tools import format_author_names


class MetaBlog(RouterForRssFeed):

    def _get_article_content(self, article_metadata, entry):

        soup = get_link_content_with_bs_no_params(article_metadata.link)

        if article_metadata.link.startswith(meta_ai_blog_prefix):
            self.__extract_ai_blog(soup, entry)
        elif article_metadata.link.startswith(meta_blog_prefix):
            # unable to extract normal meta blog now
            pass
        elif article_metadata.link.startswith(meta_blog_link):
            self.__extract_engineering_blog(soup, entry)
        else:
            pass
        return entry

    def __extract_ai_blog(self, soup, entry):

        entry_content_div = soup.find("div", {"class": "_amgj"})
        if entry_content_div:
            entry.author = soup.find('div', class_='_amgc').text

            create_time_string = soup.find('span', class_='_amum').text
            entry.created_time = convert_time_with_pattern(create_time_string, "%B %d, %Y")

            entry.description = entry_content_div
            entry.with_content = True

            entry.save_to_json(self.router_path)

    def __extract_engineering_blog(self, soup, entry):
        entry_content_div = soup.find("div", {"class": "entry-content"})
        if entry_content_div:
            for tag in entry_content_div.find_all(True):
                if tag.has_attr('style'):
                    del tag['style']

            entry.description = entry_content_div

            authors = soup.find_all(class_="author url fn")
            entry.author = format_author_names([author.text for author in authors])

            datetime_str = soup.find('time', class_='published updated')['datetime']

            entry.created_time = convert_time_with_pattern(datetime_str, '%Y-%m-%d')
            entry.with_content = True

            entry.save_to_json(self.router_path)
