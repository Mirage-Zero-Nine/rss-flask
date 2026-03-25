cnbeta_router_path = '/cnbeta'
day_one_blog_router_path = '/dayone'
earthquake_router_path = '/earthquake'
embassy_router_path = '/embassy'
jandan_router_path = '/jandan'
meta_engineering_blog_router = '/meta/blog'
reuters_news_router_path = '/reuters'
sar_router_path = "/sar"
wsdot_news_router_path = '/wsdot/news'
zaobao_router_path_prefix = "/zaobao/realtime"
# List of routers to refresh periodically
routers_to_call = [
    cnbeta_router_path,
    day_one_blog_router_path,
    earthquake_router_path,
    embassy_router_path,
    jandan_router_path,
    meta_engineering_blog_router,
    sar_router_path,
    wsdot_news_router_path,
    zaobao_router_path_prefix + '/china',
    zaobao_router_path_prefix + '/world',
    reuters_news_router_path + '/world'
]

refresh_period_in_minutes = 10

html_parser = 'html.parser'

language_chinese = "zh-cn"
language_english = "en-us"
