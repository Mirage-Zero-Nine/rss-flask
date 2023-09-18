from datetime import datetime

import pytz

from data.feed_item_object import FeedItem
from data.rss_cache import feed_item_cache
from router.base_router import BaseRouter
from utils.get_link_content import get_link_content_with_bs_no_params


class TheVergeRouter(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None):

        articles_list = []

        for i in range(0, 3):
            soup = get_link_content_with_bs_no_params(self.articles_link + str(i + 1))
            content_cards = soup.find_all("div", class_="duet--content-cards--content-card")

            for card in content_cards:
                # remove subscriber only news
                if card.find('a', href='/command-line-newsletter') is None:
                    h2_element = card.find("h2")
                    if h2_element:
                        time_element = card.find("time")
                        created_time = time_element.get("datetime")

                        href = self.original_link + h2_element.find("a")["href"]
                        author_name = card.find(
                            lambda tag: tag.name == "a" and tag.get("href", "").startswith("/authors/")).get_text()

                        extracted_datetime = datetime.strptime(str(created_time), "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                            tzinfo=pytz.utc)

                        if href not in feed_item_cache.keys():
                            feed_item = FeedItem(
                                title=h2_element.text,
                                link=href,
                                description="",
                                author=author_name,
                                guid=href,
                                created_time=extracted_datetime,
                                with_content=False
                            )

                        else:
                            feed_item = feed_item_cache.get(href)
                        articles_list.append(feed_item)

        return articles_list

    def _get_individual_article(self, entry_list):
        for entry in entry_list:
            if entry.with_content is False:
                soup = get_link_content_with_bs_no_params(entry.link)
                figure_tag = soup.find('figure', class_='duet--article--lede-image w-full')

                if figure_tag is not None:
                    img_element = figure_tag.find('img')
                    div_element = figure_tag.find('div')

                    # Remove the srcset attribute from the img tag
                    if 'srcset' in img_element.attrs:
                        del img_element['srcset']
                    if 'sizes' in img_element.attrs:
                        del img_element['sizes']
                    if 'style' in img_element.attrs:
                        del img_element['style']
                    if 'data-nimg' in img_element.attrs:
                        del img_element['data-nimg']
                    if 'decoding' in img_element.attrs:
                        del img_element['decoding']

                    entry.description = str(img_element) + str(div_element)

                content = soup.find("div", class_="duet--article--article-body-component-container")
                for element in content.find_all(True):
                    element.attrs = {key: value for key, value in element.attrs.items() if key != 'style'}

                zoom_divs = soup.find_all('div', {'aria-label': 'Zoom'})

                # Remove the found div tags
                for div in zoom_divs:
                    div.extract()

                # Find all img tags
                img_tags = soup.find_all('img')

                # Loop through each img tag
                for img_tag in img_tags:
                    # Check if the img tag has a src attribute that starts with "https://"
                    if 'src' in img_tag.attrs and img_tag['src'].startswith("https://"):
                        continue  # Skip img tags with valid src attributes
                    else:
                        img_tag.extract()  # Remove img tags without valid src attributes

                # Find all noscript tags which may have image
                noscript_tags = soup.find_all('noscript')

                # Loop through each noscript tag
                for noscript_tag in noscript_tags:
                    img_tag = noscript_tag.find('img')
                    if img_tag:
                        # Create a new img tag with only src and alt attributes
                        new_img_tag = soup.new_tag('img', src=img_tag['src'], alt=img_tag['alt'])

                        img_tag.replace_with(new_img_tag)
                        noscript_tag.replace_with(new_img_tag)

                entry.description = entry.description + str(content)
                feed_item_cache[entry.guid] = entry
