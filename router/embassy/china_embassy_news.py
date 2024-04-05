from router.base_router import BaseRouter
from router.embassy.china_embassy_news_constants import china_embassy_news_prefix, china_embassy_news_filter, \
    china_embassy_news_author
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix
from utils.get_link_content import get_link_content_with_urllib_request
from utils.time_converter import convert_time_with_pattern


class ChinaEmbassyNewsRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        soup = get_link_content_with_urllib_request(self.articles_link)
        page = soup.find("ul", {"class": "tt"})

        metadata_list = []
        for item in page:
            article = item.find('a')

            try:
                title = article.text
                link = article['href']
                if article != -1 and link_filter not in title:
                    if len(link) < 35:
                        link = china_embassy_news_prefix + link[1:]

                    save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)

                    metadata_list.append(Metadata(
                        title=title,
                        link=link,
                        guid=link,
                        author=china_embassy_news_author,
                        json_name=generate_json_name(prefix=save_json_path_prefix, name=link)
                    ))
            except AttributeError:
                continue

        return metadata_list

    def _get_article_content(self, article_metadata, entry):
        """
        Actual method to retrieve content
        :param article_metadata: metadata of article
        :param entry: object stores all the metadata and the content
        """
        soup = get_link_content_with_urllib_request(article_metadata.link)
        entry.created_time = convert_time_with_pattern(soup.find("div", id="News_Body_Time").get_text(), "%Y-%m-%d %H:%M")
        for tag in soup.find_all(True):
            tag.attrs = {key: val for key, val in tag.attrs.items() if key != 'style'}
        entry.description = soup.find('div', id='News_Body_Txt_A')
        entry.save_to_json(self.router_path)