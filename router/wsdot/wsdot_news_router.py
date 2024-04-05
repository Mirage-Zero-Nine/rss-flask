from router.base_router import BaseRouter
from router.wsdot.wsdot_news_router_constant import wsdot_news_prefix, wsdot_news_link, wsdot_blog_blogspot
from utils.feed_item_object import convert_router_path_to_save_path_prefix, Metadata, generate_json_name
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.time_converter import convert_wsdot_news_time


class WsdotNewsRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []

        for i in range(0, 3):

            # Find all elements with class "views-row"
            views_row_elements = get_link_content_with_bs_no_params(self.articles_link + '?page=' + str(i)).find_all(
                'div', class_='views-field views-field-nothing')

            # Loop through each views-row element
            for views_row in views_row_elements:
                h2_tags = views_row.find('h2')
                link = h2_tags.a.get('href')
                title = h2_tags.text
                if link and title:
                    if link.startswith("/about/news"):
                        link = wsdot_news_prefix + link

                        # sometimes the link incorrectly ending with .htm instead of .html
                    if link.endswith('htm'):
                        link += 'l'

                    save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                    metadata = Metadata(
                        title=title,
                        link=link,
                        json_name=generate_json_name(prefix=save_json_path_prefix, name=link)
                    )

                    metadata_list.append(metadata)

        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        soup = get_link_content_with_bs_no_params(article_metadata.link)

        if article_metadata.link.startswith(wsdot_blog_blogspot):
            self.__extract_wsdot_blog(soup, entry)
        else:
            self.__extract_other_news(soup, entry)

    @staticmethod
    def __extract_wsdot_blog(soup, entry):

        # Find the post content using its class name
        post_content = soup.find('div', class_='post-body entry-content')
        if post_content is not None:
            entry.description = post_content

            date_header = soup.find('h2', class_='date-header').span.text
            entry.created_time = convert_wsdot_news_time(str(date_header), "%A, %B %d, %Y")

    @staticmethod
    def __extract_other_news(soup, entry):

        post_content = soup.find('div',class_='field field--name-body field--type-text-with-summary field--label-hidden field--item')
        if post_content is not None:
            entry.description = post_content

            # Extract the datetime string from the time tag's datetime attribute
            datetime_div = soup.find('div', class_='field--name-field-date')
            datetime_string = datetime_div.find('time')['datetime']
            entry.created_time = convert_wsdot_news_time(str(datetime_string), "%Y-%m-%dT%H:%M:%SZ")
