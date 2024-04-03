cnbeta_router_path = '/cnbeta'
day_one_blog_router_path = '/dayone'
earthquake_router_path = '/earthquake'
embassy_router_path = '/embassy'
jandan_router_path = '/jandan'
meta_engineering_blog_router = '/meta/blog'
nbc_news_router_path = '/nbc/top'
telegram_wechat_router_path = '/telegram/wechat'
the_verge_router_path = '/theverge'
twitter_engineering_blog_router_path = '/twitter/blog'
wsdot_news_router_path = '/wsdot/news'
zaobao_router_path_prefix = "/zaobao/realtime"
zhihu_router_path = '/zhihu/daily'

# List of routers to refresh periodically
routers_to_call = [
    cnbeta_router_path,
    day_one_blog_router_path,
    earthquake_router_path,
    embassy_router_path,
    jandan_router_path,
    meta_engineering_blog_router,
    nbc_news_router_path,
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
china_embassy_period = 10 * 60 * 1000  # 10 minutes

jandan_time_convert_pattern = "%Y.%m.%d , %H:%M"

html_parser = 'html.parser'

jandan_page_prefix = "http://jandan.net/"

china_embassy_filter = "雇员招聘启事"
china_embassy_prefix = 'http://losangeles.china-consulate.org/tzgg'


language_chinese = "zh-cn"
language_english = "en-us"

data_path_prefix = "./data/"
