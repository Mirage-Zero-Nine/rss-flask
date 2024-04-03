from router.router_for_rss_feed import RouterForRssFeed
from router.twitter_engineering_blog.twitter_engineering_blog_router_constants import \
    twitter_engineering_blog_date_format
from utils.get_link_content import get_link_content_with_utf8_decode
from utils.time_converter import convert_time_with_pattern
from utils.tools import format_author_names


class TwitterEngineeringBlogRouter(RouterForRssFeed):
    def _get_article_content(self, article_metadata, entry):

        soup = get_link_content_with_utf8_decode(entry.link)
        author_divs = soup.select('div.blog__author--link:not(div.bl09-related-posts div.blog__author--link)')
        authors = format_author_names([div['data-account-name'] for div in author_divs])
        entry.author = authors

        create_time_text = soup.find('span', class_='b02-blog-post-no-masthead__date').text
        datetime_object = convert_time_with_pattern(
            create_time_text,
            twitter_engineering_blog_date_format
        )
        entry.created_time = datetime_object

        self.__remove_unwanted_div(soup)
        entry_content_div = soup.find("div", {"class": "column column-6"})
        entry.description = entry_content_div
        entry.with_content = True

        entry.save_to_json(self.router_path)

    @staticmethod
    def __remove_unwanted_div(soup):
        masthead_divs = soup.find_all('div', class_='bl02-blog-post-text-masthead')
        for masthead_div in masthead_divs:
            masthead_div.extract()

        tweet_error_divs = soup.find_all('div', class_='tweet-error-text')
        for tweet_error_div in tweet_error_divs:
            tweet_error_div.extract()

        tweet_template_divs = soup.find_all('div', class_='bl13-tweet-template')
        for tweet_template_div in tweet_template_divs:
            tweet_template_div.extract()

        bl14_image_divs = soup.find_all('div', class_='bl14-image')

        # remove parent div for images
        for bl14_image_div in bl14_image_divs:
            img_tag = bl14_image_div.find('img')

            # Replace data-src with src
            img_tag['src'] = img_tag['data-src']
            del img_tag['data-src']
            del img_tag['class']

            # Replace the parent div with its contents (the img tag)
            bl14_image_div.replace_with(img_tag)
