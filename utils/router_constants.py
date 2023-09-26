cnbeta_router_path = '/cnbeta'
currency_exchange_price_router_path = "/currency"
day_one_blog_router_path = '/dayone'
earthquake_router_path = '/earthquake'
embassy_router_path = '/embassy'
jandan_router_path = '/jandan'
meta_engineering_blog_router = '/meta/blog'
telegram_wechat_router_path = '/telegram/wechat'
the_verge_router_path = '/theverge'
twitter_engineering_blog_router_path = '/twitter/blog'
wsdot_news_router_path = '/wsdot/news'
zaobao_router_path_prefix = "/zaobao/realtime"
zhihu_router_path = '/zhihu/daily'

# List of routers to refresh periodically
routers_to_call = [
    cnbeta_router_path,
    # currency_exchange_price_router_path + '/usd',
    day_one_blog_router_path,
    earthquake_router_path,
    embassy_router_path,
    jandan_router_path,
    meta_engineering_blog_router,
    telegram_wechat_router_path,
    the_verge_router_path,
    twitter_engineering_blog_router_path,
    wsdot_news_router_path,
    zaobao_router_path_prefix + '/china',
    zaobao_router_path_prefix + '/world',
    zhihu_router_path
]

refresh_period_in_minutes = 10

# router query period
jandan_query_period = 1 * 60 * 60 * 1000  # 1 hour
zhihu_query_period = 1 * 60 * 60 * 1000  # 1 hour
china_embassy_period = 10 * 60 * 1000  # 10 minutes
wsdot_news_period = 10 * 60 * 1000  # 10 minutes

jandan_time_convert_pattern = "%Y.%m.%d , %H:%M"

html_parser = 'html.parser'

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

wsdot_news_link = "https://wsdot.wa.gov/about/news"
wsdot_news_prefix = "https://wsdot.wa.gov"
wsdotblog_blogspot = "https://wsdotblog.blogspot.com"

language_chinese = "zh-cn"
language_english = "en-us"

data_path_prefix = "./data/"
