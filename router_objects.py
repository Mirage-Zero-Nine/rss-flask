import yaml

from router.cnbeta.cnbeta_router import CnbetaRouter
from router.cnbeta.cnbeta_router_constants import cnbeta_news_router_title, cnbeta_news_site_link, \
    cnbeta_news_router_description, cnbeta_period, cnbeta_articles_link
from router.currency.currency_exchange_price_router import CurrencyExchangePriceRouter
from router.currency.currency_exchange_price_router_constants import currency_exchange_price_title, \
    currency_exchange_price_name, currency_exchange_price_link, currency_exchange_price_search_link, \
    currency_exchange_price_description, currency_exchange_price_cache_key, currency_exchange_price_query_period
from router.dayone.day_one_blog_constants import day_one_blog_router_title, day_one_blog_articles_link, \
    day_one_blog_site_link, day_one_blog_query_period, day_one_blog_router_description
from router.dayone.day_one_blog_router import DayOneBlogRouter
from router.earthquake.usgs_earthquake_router import UsgsEarthquakeRouter
from router.earthquake.usgs_earthquake_router_constants import usgs_earthquake_feed_title, \
    usgs_earthquake_original_link, usgs_earthquake_link, usgs_earthquake_description, usgs_earthquake_query_period
from router.meta_blog.meta_blog import MetaBlog
from router.meta_blog.meta_router_constants import meta_blog_title, meta_blog_rss_link, meta_blog_link, \
    meta_blog_description, meta_blog_period
from router.telegram.telegram_wechat_channel_router import TelegramWechatChannelRouter
from router.telegram.telegram_wechat_channel_router_constant import telegram_wechat_channel_router_title, \
    telegram_wechat_channel_router_site_link, telegram_wechat_channel_router_description, \
    telegram_wechat_channel_period, telegram_wechat_channel_url
from router.the_verge.the_verge_constants import the_verge_name, the_verge_title, the_verge_prefix, \
    the_verge_tech_archive, the_verge_description, the_verge_news_key
from router.the_verge.the_verge_router import TheVergeRouter
from router.twitter_engineering_blog.twitter_engineering_blog_router import TwitterEngineeringBlogRouter
from router.twitter_engineering_blog.twitter_engineering_blog_router_constants import twitter_engineering_blog_title, \
    twitter_engineering_blog_original_link, twitter_engineering_blog_rss_link, \
    twitter_engineering_blog_description, twitter_engineering_blog_period
from router.zaobao.zaobao_realtime_router import ZaobaoRealtimeRouter
from router.zaobao.zaobao_realtime_router_constants import zaobao_realtime_page_prefix, zaobao_query_period, \
    zaobao_region_general_title
from utils.router_constants import language_english, language_chinese, meta_engineering_blog_router, \
    twitter_engineering_blog_router_path, cnbeta_router_path, telegram_wechat_router_path, zaobao_router_path_prefix, \
    day_one_blog_router_path, earthquake_router_path

# file path started from app.py
with open('config.yml') as f:
    # use safe_load instead load
    config = yaml.safe_load(f)

meta_blog = MetaBlog(
    router_path=meta_engineering_blog_router,
    feed_title=meta_blog_title,
    original_link=meta_blog_link,
    articles_link=meta_blog_rss_link,
    description=meta_blog_description,
    language=language_english,
    period=meta_blog_period
)

cnbeta = CnbetaRouter(
    router_path=cnbeta_router_path,
    feed_title=cnbeta_news_router_title,
    original_link=cnbeta_news_site_link,
    articles_link=cnbeta_articles_link,
    description=cnbeta_news_router_description,
    language=language_chinese,
    period=cnbeta_period
)

the_verge = TheVergeRouter(
    name=the_verge_name,
    feed_title=the_verge_title,
    original_link=the_verge_prefix,
    articles_link=the_verge_tech_archive,
    description=the_verge_description,
    language=language_english,
    feed_cache_key=the_verge_news_key,
    period=cnbeta_period
)

usgs_earthquake_report = UsgsEarthquakeRouter(
    router_path=earthquake_router_path,
    feed_title=usgs_earthquake_feed_title,
    original_link=usgs_earthquake_original_link,
    articles_link=usgs_earthquake_link,
    description=usgs_earthquake_description,
    language=language_english,
    period=usgs_earthquake_query_period
)

currency_exchange_price = CurrencyExchangePriceRouter(
    name=currency_exchange_price_name,
    feed_title=currency_exchange_price_title,
    original_link=currency_exchange_price_link,
    articles_link=currency_exchange_price_search_link,
    description=currency_exchange_price_description,
    language=language_chinese,
    feed_cache_key=currency_exchange_price_cache_key,
    period=currency_exchange_price_query_period
)

twitter_engineering_blog = TwitterEngineeringBlogRouter(
    router_path=twitter_engineering_blog_router_path,
    feed_title=twitter_engineering_blog_title,
    original_link=twitter_engineering_blog_original_link,
    articles_link=twitter_engineering_blog_rss_link,
    description=twitter_engineering_blog_description,
    language=language_english,
    period=twitter_engineering_blog_period
)

telegram_wechat_channel = TelegramWechatChannelRouter(
    router_path=telegram_wechat_router_path,
    feed_title=telegram_wechat_channel_router_title,
    original_link=telegram_wechat_channel_router_site_link,
    articles_link=config[telegram_wechat_channel_url],
    description=telegram_wechat_channel_router_description,
    language=language_chinese,
    period=telegram_wechat_channel_period
)

zaobao_realtime = ZaobaoRealtimeRouter(
    router_path=zaobao_router_path_prefix,
    feed_title=zaobao_region_general_title,
    articles_link=zaobao_realtime_page_prefix,
    language=language_chinese,
    period=zaobao_query_period
)

day_one_blog = DayOneBlogRouter(
    router_path=day_one_blog_router_path,
    feed_title=day_one_blog_router_title,
    original_link=day_one_blog_site_link,
    articles_link=day_one_blog_articles_link,
    description=day_one_blog_router_description,
    language=language_english,
    period=day_one_blog_query_period
)