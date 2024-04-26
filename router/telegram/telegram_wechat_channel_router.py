from router.base_router import BaseRouter
from router.telegram.telegram_wechat_channel_router_constant import telegram_wechat_channel_link_filter, \
    telegram_wechat_channel_router_description
from utils.feed_item_object import Metadata, generate_json_name, convert_router_path_to_save_path_prefix
from utils.get_link_content import get_link_content_with_bs_no_params, \
    get_content_with_utf8_decode_and_disable_verification
from utils.time_converter import convert_time_with_pattern
from utils.tools import check_need_to_filter, remove_empty_tag


class TelegramWechatChannelRouter(BaseRouter):
    def _get_articles_list(self, link_filter=None, title_filter=None, parameter=None):
        # list of metadata of the articles
        metadata_list = []

        soup = get_link_content_with_bs_no_params(self.articles_link)
        message_bubble_divs = soup.find_all('div', class_='tgme_widget_message_bubble')

        for message_bubble_div in message_bubble_divs:

            link_elements = message_bubble_div.find_all('a', {
                'onclick': "return confirm('Open this link?\\n\\n'+this.href);", 'rel': 'noopener', 'target': '_blank'})
            for link_element in link_elements:
                href = link_element['href']

                # there are multiple links in the selected div, only need the link starts with http://mp.weixin.qq.com/
                if telegram_wechat_channel_link_filter in href:

                    save_json_path_prefix = convert_router_path_to_save_path_prefix(self.router_path)
                    if href.startswith('http://'):
                        href = href.replace('http://', 'https://')
                        href = self.__remove_tracker(href)

                    entry_title = link_element.text.strip()
                    entry_creat_time = message_bubble_div.find('time', class_='time')['datetime']

                    if check_need_to_filter(href, entry_title, link_filter, title_filter) is False:
                        metadata = Metadata(title=entry_title,
                                            link=href,
                                            created_time=entry_creat_time,
                                            json_name=generate_json_name(prefix=save_json_path_prefix, name=href))
                        metadata_list.append(metadata)

        return metadata_list

    def _get_article_content(self, article_metadata, entry):

        entry.author = telegram_wechat_channel_router_description
        entry.created_time = convert_time_with_pattern(article_metadata.created_time, "%Y-%m-%dT%H:%M:%S%z")

        soup = get_content_with_utf8_decode_and_disable_verification(article_metadata.link)

        selected_div = soup.find("div", class_=lambda
            x: x and "rich_media_content" in x.split() and "js_underline_content" in x.split())
        if selected_div and 'style' in selected_div.attrs:
            del selected_div['style']
        if selected_div:
            mpaudio_section = selected_div.find('mp-common-mpaudio')
            if mpaudio_section:
                mpaudio_parent_section = mpaudio_section.find_parent('section')
                mpaudio_parent_section.extract()
            for tag in selected_div.find_all(True):
                tag.attrs = {key: value for key, value in tag.attrs.items() if key.lower() != 'style'}

        img_tags = soup.find_all('img', class_="rich_pages wxw-img")
        for img_tag in img_tags:
            # Replace data-src with src and remove all other attributes
            img_tag.attrs = {'src': img_tag['data-src']}

        # remove empty p and section tag
        try:
            remove_empty_tag(selected_div, "p")
        except AttributeError:
            pass
        try:
            remove_empty_tag(selected_div, "section")
        except AttributeError:
            pass

        entry.description = selected_div
        entry.save_to_json(self.router_path)

        return entry

    @staticmethod
    def __remove_tracker(url):
        if "&amp;chksm=" in url:
            return url.split("&amp;chksm=")[0]

        return url
