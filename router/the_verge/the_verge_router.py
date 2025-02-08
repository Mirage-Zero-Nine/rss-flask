import logging
from datetime import datetime

from router.base_router import BaseRouter
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix, FeedItem
from utils.get_link_content import get_link_content_with_bs_no_params


class TheVergeRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []

        for i in range(0, 5):
            soup = get_link_content_with_bs_no_params(self.articles_link + str(i + 1))
            all_updates = soup.find_all('div', class_=lambda c: c and all(
                cls in c for cls in ['duet--content-cards--content-card']))
            for update in all_updates:
                href, flag = None, None
                a_tag = update.find('span', class_='coral-count')
                if a_tag:
                    href = a_tag.get('data-coral-url')
                if href:
                    if 'duet--content-cards--quick-post' not in update.get('class', []):
                        flag = 'full-post'
                    else:
                        flag = 'short'
                if href:
                    save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                    metadata = Metadata(
                        link=href,
                        json_name=generate_json_name(prefix=save_json_path_prefix, name=href),
                        flag=flag
                    )
                    metadata_list.append(metadata)

        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        soup = get_link_content_with_bs_no_params(article_metadata.link)
        entry.link = article_metadata.link
        title_tag = soup.find('meta', attrs={'name': 'parsely-title'})
        author_tag = soup.find('meta', attrs={'name': 'author'})
        creation_tag = soup.find('meta', attrs={'name': 'parsely-pub-date'})
        entry.title = title_tag['content'] if title_tag else None
        entry.author = author_tag['content'] if author_tag else None
        entry.created_time = datetime.strptime(creation_tag['content'],
                                               "%Y-%m-%dT%H:%M:%S%z") if creation_tag else None
        entry.description = ""

        if article_metadata.flag == 'full-post':
            self._get_content_for_full_post(entry, soup)
        elif article_metadata.flag == 'short':
            self._get_short_post_content(entry, soup)

        entry.save_to_json(self.router_path)

        return entry

    def _get_content_for_full_post(self, entry: FeedItem, soup):
        logging.info("Getting content from article {}".format(entry.link))

        self._process_metadata(soup, entry)
        self._process_title_image(soup, entry)
        self._processing_body(soup, entry)

    @staticmethod
    def _process_metadata(soup, entry: FeedItem):
        metadata_tag = soup.find('div', class_='duet--article--lede duet--page-layout--feature-article')
        if metadata_tag:
            h1 = metadata_tag.find('h1')
            if h1:
                entry.title = h1.text
        markup = soup.find('p', class_='duet--article--dangerously-set-cms-markup')
        if markup:
            entry.description += str(markup)

    def _process_title_image(self, soup, entry: FeedItem):
        metadata_tag = soup.find('div', class_='duet--article--lede')
        if metadata_tag:
            img_src = metadata_tag.find('img')
            if img_src:
                if img_src.get('src'):
                    entry.description += f'<img src="{img_src.get("src")}" alt="title image" />'
                    caption = metadata_tag.find('div', class_='duet--media--caption')
                    if caption:
                        entry.description += str(caption)

    def _processing_body(self, soup, entry: FeedItem):
        body = soup.find('div', class_='duet--layout--entry-body')
        self._remove_empty_div(body)
        if body:
            entry.description += str(body)

    def _get_short_post_content(self, entry: FeedItem, soup):
        body_tag = soup.find('div', class_='duet--content-cards--quick-post')
        for svg in body_tag.find_all('svg'):
            svg.decompose()
        for span in body_tag.find_all('span'):
            span.decompose()
        for a in body_tag.find_all('a', class_='duet--article--comments-link'):
            a.decompose()
        for div in body_tag.find_all('div'):
            if len(div.get_text(strip=True)) == 1:
                div.decompose()
        for div in body_tag.find_all('div'):
            if div.get_text(strip=True) == entry.title:
                div.decompose()
        self._remove_empty_div(body_tag)
        entry.description += str(body_tag) if body_tag else None

    @staticmethod
    def _remove_empty_div(soup):
        for div in soup.find_all('div'):
            if not div.get_text(strip=True):
                div.decompose()