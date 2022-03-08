import requests
from bs4 import BeautifulSoup
from flask import make_response

import constant.constants as c
import router.zaobao.data_object as do
import utils.generate_xml as gxml
import utils.time_convert as tc

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Referer': 'https://www.zaobao.com.sg/realtime',
    'Host': 'www.zaobao.com.sg',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0'
}


def get_news_list():
    data = requests.get('https://www.zaobao.com.sg/realtime/world?_wrapper_format=html&page=1', headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')
    news_list = soup.find_all("div", {"class": "col col-lg-12"})  # type is bs4.element.ResultSet
    output_news_list = []
    for news in news_list:
        news_item = do.NewsItem()
        news_item.title = news.find('a').contents[0].text
        news_item.link = c.zaobao_story_prefix + news.find('a')['href']
        output_news_list.append(news_item)

    return output_news_list


def get_individual_news_content(news_list):
    for item in news_list:
        soup = get_link_content(item.link)
        post_list = soup.find_all(
            'div',
            {'class': 'article-content-rawhtml'}
        )
        title_list = soup.find_all(
            'h4',
            {'class': 'title-byline byline'}
        )
        time_list = soup.find_all(
            'h4',
            {'class': 'title-byline date-published'}
        )
        news_text = ''
        for t in time_list:
            item.created_time = t.text.split('/')[1].strip()
        for e in title_list:
            item.author = e.find_all('a')[0].text.strip()
        for post in post_list:
            # print(str(post))

            for text in post.find_all('p'):
                news_text += str(text)
            item.description = news_text


def get_link_content(link):
    data = requests.get(link, headers=headers)
    soup = BeautifulSoup(data.text, 'html.parser')
    return soup


def generate_news_rss_feed():
    news_list = get_news_list()
    get_individual_news_content(news_list)
    item_list = []

    for i in news_list:
        item = gxml.create_item(
            title=i.title,
            link=i.link,
            description=i.description,
            author=i.author,
            guid=i.link,
            pubDate=tc.convert_time_zaobao(i.created_time)
        )

        item_list.append(item)

    feed = gxml.generate_feed(
        title="联合早报 - 国际即时新闻",
        link=c.zaobao_realtime_frontpage_prefix,
        description="新加坡、中国、亚洲和国际的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。",
        language="zh-cn",
        items=item_list
    )
    response = make_response(feed)
    response.headers.set('Content-Type', 'application/rss+xml')
    return response


if __name__ == '__main__':
    # pass

    list = get_news_list()
    get_individual_news_content(list)
    # generate_news_rss_feed()
    # print(list)
