import yaml
import logging
from router.cnbeta.cnbeta_router import CnbetaRouter
from router.cnbeta.cnbeta_router_constants import cnbeta_news_router_title, cnbeta_news_site_link, \
    cnbeta_news_router_description, cnbeta_period, cnbeta_articles_link
from router.dayone.day_one_blog_constants import day_one_blog_router_title, day_one_blog_articles_link, \
    day_one_blog_site_link, day_one_blog_query_period, day_one_blog_router_description
from router.dayone.day_one_blog_router import DayOneBlogRouter
from router.earthquake.usgs_earthquake_router import UsgsEarthquakeRouter
from router.earthquake.usgs_earthquake_router_constants import usgs_earthquake_feed_title, \
    usgs_earthquake_original_link, usgs_earthquake_link, usgs_earthquake_description, usgs_earthquake_query_period
from router.embassy.china_embassy_news import ChinaEmbassyNewsRouter
from router.embassy.china_embassy_news_constants import china_embassy_news_title, china_embassy_news_prefix, \
    china_embassy_news_description, china_embassy_news_period
from router.jandan.jandan_constant import jandan_query_period, jandan_page_prefix, jandan_title, jandan_description
from router.jandan.jandan_router import JandanRouter
from router.meta_blog.meta_tech_blog_router import MetaBlog
from router.meta_blog.meta_tech_blog_router_constants import meta_blog_title, meta_blog_rss_link, meta_blog_link, \
    meta_blog_description, meta_blog_period
from router.nbc_news.nbc_news_router import NbcNewsRouter
from router.nbc_news.nbc_news_router_constants import nbc_news_title, nbc_news_original_link, nbc_news_rss_link, \
    nbc_news_description, nbc_news_period
from router.reuters.reuters_constants import reuters_fetch_api_base_link, reuters_site_link, reuters_description, \
    reuters_period, reuters_news_name
from router.reuters.reuters_router import ReutersRouter
from router.sony_alpha_rumor.sony_alpha_rumor_router import SonyAlphaRumorsRouter
from router.sony_alpha_rumor.sony_alpha_rumor_router_constants import sar_name, sar_link, sar_rss_link, \
    sar_query_period, sar_description
from router.the_verge.the_verge_constants import the_verge_title, the_verge_prefix, the_verge_archive, \
    the_verge_description
from router.the_verge.the_verge_router import TheVergeRouter
from router.twitter_engineering_blog.twitter_engineering_blog_router import TwitterEngineeringBlogRouter
from router.twitter_engineering_blog.twitter_engineering_blog_router_constants import twitter_engineering_blog_title, \
    twitter_engineering_blog_original_link, twitter_engineering_blog_rss_link, \
    twitter_engineering_blog_description, twitter_engineering_blog_period
from router.wsdot.wsdot_news_router import WsdotNewsRouter
from router.wsdot.wsdot_news_router_constant import wsdot_news_title, wsdot_news_link, wsdot_news_description, \
    wsdot_news_period
from router.zaobao.zaobao_realtime_router import ZaobaoRealtimeRouter
from router.zaobao.zaobao_realtime_router_constants import zaobao_realtime_page_prefix, zaobao_query_period, \
    zaobao_region_general_title
from router.zhihu.zhihu_daily_router import ZhihuDailyRouter
from router.zhihu.zhihu_daily_router_constants import zhihu_daily_title, zhihu_daily_link, zhihu_daily_description, \
    zhihu_query_period
from utils.router_constants import language_english, language_chinese, meta_engineering_blog_router, \
    twitter_engineering_blog_router_path, cnbeta_router_path, zaobao_router_path_prefix, \
    day_one_blog_router_path, earthquake_router_path, the_verge_router_path, nbc_news_router_path, \
    wsdot_news_router_path, zhihu_router_path, embassy_router_path, jandan_router_path, reuters_news_router_path, \
    sar_router_path

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.INFO)

config = None

try:
    with open('config.yml') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    logging.warning("Warning: Config file not found.")
except yaml.YAMLError as e:
    logging.warning(f"Warning: Failed to parse YAML file. Details: {e}. ")
except Exception as e:
    logging.warning(f"Warning: An unexpected error occurred: {e}.")

meta_tech_blog = MetaBlog(
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
    router_path=the_verge_router_path,
    feed_title=the_verge_title,
    original_link=the_verge_prefix,
    articles_link=the_verge_archive,
    description=the_verge_description,
    language=language_english,
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

twitter_engineering_blog = TwitterEngineeringBlogRouter(
    router_path=twitter_engineering_blog_router_path,
    feed_title=twitter_engineering_blog_title,
    original_link=twitter_engineering_blog_original_link,
    articles_link=twitter_engineering_blog_rss_link,
    description=twitter_engineering_blog_description,
    language=language_english,
    period=twitter_engineering_blog_period
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

nbc_news = NbcNewsRouter(
    router_path=nbc_news_router_path,
    feed_title=nbc_news_title,
    original_link=nbc_news_original_link,
    articles_link=nbc_news_rss_link,
    description=nbc_news_description,
    language=language_english,
    period=nbc_news_period
)

wsdot_news = WsdotNewsRouter(
    router_path=wsdot_news_router_path,
    feed_title=wsdot_news_title,
    original_link=wsdot_news_link,
    articles_link=wsdot_news_link,
    description=wsdot_news_description,
    language=language_english,
    period=wsdot_news_period
)

zhihu_daily = ZhihuDailyRouter(
    router_path=zhihu_router_path,
    feed_title=zhihu_daily_title,
    original_link=zhihu_daily_link,
    articles_link=zhihu_daily_link,
    description=zhihu_daily_description,
    language=language_chinese,
    period=zhihu_query_period
)

chinese_embassy_news = ChinaEmbassyNewsRouter(
    router_path=embassy_router_path,
    feed_title=china_embassy_news_title,
    original_link=china_embassy_news_prefix,
    articles_link=china_embassy_news_prefix,
    description=china_embassy_news_description,
    language=language_chinese,
    period=china_embassy_news_period
)

jandan_news = JandanRouter(
    router_path=jandan_router_path,
    feed_title=jandan_title,
    original_link=jandan_page_prefix,
    articles_link=jandan_page_prefix,
    description=jandan_description,
    language=language_chinese,
    period=jandan_query_period
)

reuters_news = ReutersRouter(
    router_path=reuters_news_router_path,
    feed_title=reuters_news_name,
    original_link=reuters_site_link,
    articles_link=reuters_fetch_api_base_link,
    description=reuters_description,
    language=language_english,
    period=reuters_period
)

sony_alpha_rumors = SonyAlphaRumorsRouter(
    router_path=sar_router_path,
    feed_title=sar_name,
    original_link=sar_link,
    articles_link=sar_rss_link,
    description=sar_description,
    language=language_english,
    period=sar_query_period
)
