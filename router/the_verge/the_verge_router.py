import logging
from datetime import datetime

from bs4 import BeautifulSoup

from router.base_router import BaseRouter
from router.the_verge.the_verge_constants import the_verge_prefix
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix, FeedItem
from utils.get_link_content import get_link_content_with_bs_no_params


class TheVergeRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):

        metadata_list = []

        for i in range(0, 3):
            soup = get_link_content_with_bs_no_params(self.articles_link + str(i + 1))
            all_updates = soup.find('div', class_='mx-auto w-full').find_all('div', class_=lambda c: c and all(
                cls in c for cls in ['duet--content-cards--content-card', 'relative', 'flex flex-row']))
            for update in all_updates:
                h2 = update.find('h2')
                a_tag = update.find('a', class_='hover:shadow-underline-inherit after:absolute after:inset-0')
                if h2:
                    a = update.find('h2').find('a')
                    href = the_verge_prefix + a.get('href') if a else None
                    flag = 'full-post'
                elif a_tag:
                    href = the_verge_prefix + a_tag.get('href')
                    flag = 'short'
                else:
                    href, flag = None, None
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
        author_tag = soup.find('meta', attrs={'property': 'author'})
        creation_tag = soup.find('meta', attrs={'name': 'parsely-pub-date'})
        entry.title = title_tag['content'] if title_tag else None
        entry.author = author_tag['content'] if author_tag else None
        entry.created_time = datetime.strptime(creation_tag['content'],
                                               "%Y-%m-%dT%H:%M:%S.%fZ") if creation_tag else None
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
        sub_title = soup.find('div', class_='mb-24 grow')
        if sub_title is None:
            sub_title = soup.find('div', class_='mb-18')
        if sub_title:
            entry.description += str(sub_title.find('h2'))

        byline_tag = soup.find('p', class_=lambda c: c and all(
            cls in c for cls in ['duet--article--article-byline max-w-[550px]']))
        entry.description += str(byline_tag) if byline_tag else None

    def _process_title_image(self, soup, entry: FeedItem):
        img_div = soup.find('div', class_='w-full shrink-0 lg:basis-[600px]')
        if img_div is None:
            img_div = soup.find('div', class_='md:hidden')
        if img_div:
            img_tag = img_div.find('img')
            if img_tag:
                self._remove_attr_in_img(img_tag)
                entry.description += str(img_tag) if img_tag else None

    def _processing_body(self, soup, entry: FeedItem):
        body_tag = soup.find('div', class_=lambda c: c and all(
            cls in c for cls in ['duet--article--article-body-component-container']))
        parent_divs = body_tag.find_all('div', class_=lambda c: c and all(
            cls in c for cls in ['duet--article--article-body-component', 'clear-both', 'block']))
        for parent_div in parent_divs:
            zoom_divs = parent_div.find_all('div', attrs={'aria-label': 'Zoom'})
            for zoom_div in zoom_divs:
                zoom_div.decompose()
            image_tag_containers = parent_div.find_all('figure')
            if not image_tag_containers:
                image_tag_containers = parent_div.find_all('div',
                                                           class_=lambda c: c and all(
                                                               cls in c for cls in
                                                               ['relative', 'transition', 'duration-75', 'ease-in-out',
                                                                'p-0']))
            if image_tag_containers:
                for image_tag_container in image_tag_containers:
                    noscript_tag = image_tag_container.find('noscript')
                    if noscript_tag:
                        img_tag = BeautifulSoup(noscript_tag.decode_contents(), 'html.parser').find('img')
                        if img_tag:
                            self._remove_attr_in_img(img_tag)
                            image_tag_container.replace_with(img_tag)

        comment_div = soup.find('div', class_='mb-40 mt-30')
        if comment_div:
            comment_div.decompose()

            entry.description += str(body_tag) if body_tag else None

    @staticmethod
    def _get_short_post_content(entry: FeedItem, soup):
        body_tag = soup.find('div', class_='font-polysans text-black dark:text-gray-ef leading-130')
        unwanted_div = soup.find('div', class_='inline pr-4 text-17 font-bold md:text-17')
        if unwanted_div:
            unwanted_div.decompose()
        entry.description += str(body_tag) if body_tag else None

    @staticmethod
    def _remove_attr_in_img(img_tag):
        if 'srcset' in img_tag.attrs:
            del img_tag['srcset']
        if 'style' in img_tag.attrs:
            del img_tag['style']
        if 'data-nimg' in img_tag.attrs:
            del img_tag['data-nimg']
        if 'decoding' in img_tag.attrs:
            del img_tag['decoding']
        if 'sizes' in img_tag.attrs:
            del img_tag['sizes']
