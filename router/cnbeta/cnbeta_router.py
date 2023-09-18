from data.feed_item_object import FeedItem
from data.rss_cache import feed_cache, feed_item_cache
from router.base_router import BaseRouter
from router.cnbeta.cnbeta_router_constants import cnbeta_query_page_count, cnbeta_articles_link, cnbeta_news_router_name
from utils.get_link_content import get_link_content_with_utf8_decode
from utils.time_converter import convert_time_with_pattern


class CnbetaRouter(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None):
        articles_list = []

        for i in range(0, cnbeta_query_page_count):
            link = f"{self.articles_link}/list/latest_{i + 1}.htm"
            soup = get_link_content_with_utf8_decode(link)

            ul_element = soup.find('ul', class_='info_list')
            txt_area_divs = ul_element.find_all('div', class_='txt_area')

            for div in txt_area_divs:
                a_tag = div.find('a')
                href = a_tag.get('href')
                title = a_tag.find('p', class_='txt_detail').text if a_tag.find('p', class_='txt_detail') else None
                link = cnbeta_articles_link + href

                if link and title:
                    if link in feed_cache.keys():
                        news_item = feed_item_cache[link]
                    else:
                        news_item = FeedItem(title=title,
                                             link=link,
                                             guid=link,
                                             with_content=False)
                    articles_list.append(news_item)

        return articles_list

    def _get_individual_article(self, entry_list):
        for entry in entry_list:
            if entry.with_content is False:
                soup = get_link_content_with_utf8_decode(entry.link)
                time_object = self.__extract_time(soup)
                entry.created_time = convert_time_with_pattern(time_object, '%Y-%m-%d %H:%M:%S', 8)
                entry.description = self.__extract_content(soup)
                entry.author = cnbeta_news_router_name  # they don't have a specific author
                feed_item_cache[entry.guid] = entry

    def __extract_time(self, soup):
        time_element = soup.find('time', class_='time')
        return time_element.get_text() if time_element else None

    def __extract_content(self, soup):
        article_cont_div = soup.find('div', class_='articleCont')
        return article_cont_div.decode_contents() if article_cont_div else None
