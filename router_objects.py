from router.cnbeta.cnbeta_router import CnbetaRouter
from router.cnbeta.cnbeta_router_constants import cnbeta_news_router_title, \
    cnbeta_news_site_link, cnbeta_news_router_cache_key, cnbeta_news_router_description, cnbeta_period, \
    cnbeta_articles_link
from router.currency.currency_exchange_price_router import CurrencyExchangePriceRouter
from router.currency.currency_exchange_price_router_constants import currency_exchange_price_title, \
    currency_exchange_price_name, currency_exchange_price_link, currency_exchange_price_search_link, \
    currency_exchange_price_description, currency_exchange_price_cache_key, currency_exchange_price_query_period
from router.earthquake.usgs_earthquake_router import UsgsEarthquakeRouter
from router.earthquake.usgs_earthquake_router_constants import usgs_earthquake_name, usgs_earthquake_feed_title, \
    usgs_earthquake_original_link, usgs_earthquake_link, usgs_earthquake_description, usgs_earthquake_cache_key, \
    usgs_earthquake_query_period
from router.meta_blog.meta_blog import MetaBlog
from router.meta_blog.meta_router_constants import meta_blog_title, meta_blog_rss_link, \
    meta_blog_link, meta_blog_description, meta_blog_key, meta_blog_period
from router.the_verge.the_verge_constants import the_verge_name, the_verge_title, the_verge_prefix, \
    the_verge_tech_archive, the_verge_description, the_verge_news_key
from router.the_verge.the_verge_router import TheVergeRouter
from router.twitter_engineering_blog.twitter_engineering_blog_router import TwitterEngineeringBlogRouter
from router.twitter_engineering_blog.twitter_engineering_blog_router_constants import twitter_engineering_blog_title, \
    twitter_engineering_blog_original_link, twitter_engineering_blog_rss_link, \
    twitter_engineering_blog_description, twitter_engineering_blog_key, twitter_engineering_blog_period
from utils.router_constants import language_english, language_chinese, meta_engineering_blog_router, \
    twitter_engineering_blog_router_path, cnbeta_router_path

meta_blog = MetaBlog(
    router_path=meta_engineering_blog_router,
    feed_title=meta_blog_title,
    original_link=meta_blog_link,
    articles_link=meta_blog_rss_link,
    description=meta_blog_description,
    language=language_english,
    feed_cache_key=meta_blog_key,
    period=meta_blog_period
)

cnbeta = CnbetaRouter(
    router_path=cnbeta_router_path,
    feed_title=cnbeta_news_router_title,
    original_link=cnbeta_news_site_link,
    articles_link=cnbeta_articles_link,
    description=cnbeta_news_router_description,
    language=language_chinese,
    feed_cache_key=cnbeta_news_router_cache_key,
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
    name=usgs_earthquake_name,
    feed_title=usgs_earthquake_feed_title,
    original_link=usgs_earthquake_original_link,
    articles_link=usgs_earthquake_link,
    description=usgs_earthquake_description,
    language=language_english,
    feed_cache_key=usgs_earthquake_cache_key,
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
    feed_cache_key=twitter_engineering_blog_key,
    period=twitter_engineering_blog_period
)
