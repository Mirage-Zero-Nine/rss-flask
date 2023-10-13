import logging
import os
from datetime import datetime

import pytz

from router.base_router import BaseRouter
from utils.feed_item_object import FeedItem, read_feed_item_from_json, Metadata, generate_json_name, \
    convert_router_path_to_save_path_prefix
from utils.get_link_content import get_link_content_with_bs_no_params


class TheVergeRouter(BaseRouter):
    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):

        metadata_list = []

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
                        author_name = (card.find("div",
                                                 class_="relative z-10 inline-block pt-4 font-polysans text-11 uppercase leading-140 tracking-15 text-gray-31 dark:text-gray-bd").find(
                            'div', class_='inline-block').get_text())
                        save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                        metadata = Metadata(
                            title=h2_element.text,
                            link=href,
                            author=author_name,
                            created_time=str(created_time),
                            json_name=generate_json_name(prefix=save_json_path_prefix, name=href)
                        )
                        metadata_list.append(metadata)

        return metadata_list

    def _get_individual_article(self, article_metadata):

        if os.path.exists(article_metadata.json_name):
            entry = read_feed_item_from_json(article_metadata.json_name)
        else:
            logging.info(f"Getting content for: {article_metadata.link}")
            entry = FeedItem(title=article_metadata.title,
                             link=article_metadata.link,
                             guid=article_metadata.link,
                             created_time=datetime.strptime(article_metadata.created_time,
                                                            "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=pytz.utc),
                             author=article_metadata.author,
                             description="")
            soup = get_link_content_with_bs_no_params(entry.link)

            zoom_divs = soup.find_all('div', {'aria-label': 'Zoom'})
            for div in zoom_divs:
                div.extract()

            # Find all img tags
            img_tags = soup.find_all('img')
            for img_tag in img_tags:
                # Check if the img tag has a src attribute that starts with "https://"
                if 'src' in img_tag.attrs and img_tag['src'].startswith("https://"):
                    continue  # Skip img tags with valid src attributes
                else:
                    img_tag.extract()  # Remove img tags without valid src attributes

            # Find all noscript tags which may have image
            noscript_tags = soup.find_all('noscript')
            for noscript_tag in noscript_tags:
                img_tag = noscript_tag.find('img')
                if img_tag:
                    # Create a new img tag with only src and alt attributes
                    new_img_tag = soup.new_tag('img', src=img_tag['src'], alt=img_tag['alt'])

                    img_tag.replace_with(new_img_tag)
                    noscript_tag.replace_with(new_img_tag)

            h2_div = soup.find('h2', class_='inline selection:bg-franklin-20')
            if h2_div:
                entry.description += f"<p>{h2_div.get_text()}</p>"

            p_div = soup.find('p', class_='duet--article--article-byline')
            if p_div:
                entry.description += f"<p>{p_div.get_text()}</p>"

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

                entry.description = entry.description + str(img_element) + str(div_element)

            content = soup.find_all("div", class_="duet--article--article-body-component-container")
            for element in content:
                element.attrs = {key: value for key, value in element.attrs.items() if key != 'style'}

                p_tags = element.find_all('p')
                for p_tag in p_tags:
                    if p_tag.has_attr('class'):
                        del p_tag['class']

                div_tags = element.find_all('div')
                for div_tag in div_tags:
                    if div_tag.has_attr('class'):
                        del div_tag['class']

            entry.description = entry.description + str(content)
            entry.save_to_json(self.router_path)

        return entry


#
if __name__ == '__main__':
    soup = get_link_content_with_bs_no_params(
        "https://www.theverge.com/2023/10/12/23914862/eu-x-elon-musk-european-commission-probe-dsa-digital-services-act-hamas-israel")
    print(soup)
#     h2_div = soup.find('h2', class_='inline selection:bg-franklin-20')
#     print(h2_div.get_text())
#
#     p_div = soup.find('p', class_='duet--article--article-byline')
#     print(p_div.get_text())
