# List of routers to refresh periodically
routers_to_call = [
    '/cnbeta',
    '/currency/usd',
    '/dayone',
    '/earthquake',
    '/embassy',
    '/jandan',
    "/meta/blog",
    '/telegram/wechat',
    '/theverge',
    '/twitter/blog',
    '/wsdot/news',
    '/zaobao/realtime/china',
    '/zaobao/realtime/world',
    '/zhihu/daily'
]

refresh_period_in_minutes = 10

# router query period
jandan_query_period = 1 * 60 * 60 * 1000  # 1 hour
dayone_query_period = 1 * 60 * 60 * 1000  # 1 hour
zaobao_query_period = 10 * 60 * 1000  # 10 minutes
zhihu_query_period = 1 * 60 * 60 * 1000  # 1 hour
china_embassy_period = 10 * 60 * 1000  # 10 minutes
telegram_wechat_channel_period = 30 * 60 * 1000  # 30 minutes
wsdot_news_period = 10 * 60 * 1000  # 10 minutes

zaobao_time_convert_pattern = "%Y年%m月%d日 %I:%M %p"
dayone_time_convert_pattern = '%B %d, %Y'
jandan_time_convert_pattern = "%Y.%m.%d , %H:%M"

html_parser = 'html.parser'

zaobao_realtime_world_frontpage_prefix = "https://www.zaobao.com.sg/realtime/world"
zaobao_realtime_china_frontpage_prefix = "https://www.zaobao.com.sg/realtime/china"
zaobao_story_prefix = 'https://www.zaobao.com.sg'
zaobao_realtime_world_page_prefix = 'https://www.zaobao.com.sg/realtime/world?_wrapper_format=html&page='
zaobao_realtime_page_prefix = "https://www.zaobao.com.sg/realtime/"
zaobao_realtime_page_suffix = "?_wrapper_format=html&page="
zaobao_region_world = "world"
zaobao_region_china = "china"

zaobao_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Referer': 'https://www.zaobao.com.sg/realtime',
    'Host': 'www.zaobao.com.sg',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0'
}

dayone_blog_link = "https://dayoneapp.com/blog/"

jandan_page_prefix = "http://jandan.net/"

zhihu_header = {
    "Host": "daily.zhihu.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0",
    "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

zhihu_story_prefix = "https://daily.zhihu.com"
zhihu_filter = "瞎扯 · "

china_embassy_filter = "雇员招聘启事"
china_embassy_prefix = 'http://losangeles.china-consulate.org/tzgg'

telegram_wechat_channel_url = 'telegram_wechat_channel_url'

wsdot_news_link = "https://wsdot.wa.gov/about/news"
wsdot_news_prefix = "https://wsdot.wa.gov"
wsdotblog_blogspot = "https://wsdotblog.blogspot.com"

language_chinese = "zh-cn"
language_english = "en-us"
