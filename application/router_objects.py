from router.apnews.apnews_router import ApnewsRouter
from router.apnews.apnews_router_constants import (
    apnews_feed_title,
    apnews_original_link,
    apnews_articles_link,
    apnews_description,
    apnews_business_feed_title,
    apnews_business_original_link,
    apnews_business_articles_link,
    apnews_business_description,
)
from router.cnbeta.cnbeta_router import CnbetaRouter
from router.cnbeta.cnbeta_router_constants import (
    cnbeta_news_router_title,
    cnbeta_news_site_link,
    cnbeta_news_router_description,
    cnbeta_articles_link,
)
from router.dayone.day_one_blog_constants import (
    day_one_blog_router_title,
    day_one_blog_articles_link,
    day_one_blog_site_link,
    day_one_blog_router_description,
)
from router.dayone.day_one_blog_router import DayOneBlogRouter
from router.earthquake.usgs_earthquake_router import UsgsEarthquakeRouter
from router.earthquake.usgs_earthquake_router_constants import (
    usgs_earthquake_feed_title,
    usgs_earthquake_original_link,
    usgs_earthquake_link,
    usgs_earthquake_description,
)
from router.embassy.china_embassy_news import ChinaEmbassyNewsRouter
from router.embassy.china_embassy_news_constants import (
    china_embassy_news_title,
    china_embassy_news_prefix,
    china_embassy_news_description,
)
from router.jandan.jandan_constant import jandan_page_prefix, jandan_title, jandan_description
from router.jandan.jandan_router import JandanRouter
from router.meta_blog.meta_tech_blog_router import MetaBlog
from router.meta_blog.meta_tech_blog_router_constants import (
    meta_blog_title,
    meta_blog_rss_link,
    meta_blog_link,
    meta_blog_description,
)
from router.openai_news.openai_news_router import OpenAINewsRouter
from router.openai_news.openai_news_router_constants import (
    openai_news_feed_title,
    openai_news_original_link,
    openai_news_articles_link,
    openai_news_description,
    openai_news_period,
)
from router.reuters.reuters_constants import (
    reuters_fetch_api_base_link,
    reuters_site_link,
    reuters_description,
    reuters_news_name,
)
from router.reuters.reuters_router import ReutersRouter
from router.sony_alpha_rumor.sony_alpha_rumor_router import SonyAlphaRumorsRouter
from router.sony_alpha_rumor.sony_alpha_rumor_router_constants import (
    sar_name,
    sar_link,
    sar_rss_link,
    sar_description,
)
from router.wsdot.wsdot_news_router import WsdotNewsRouter
from router.wsdot.wsdot_news_router_constant import wsdot_news_title, wsdot_news_link, wsdot_news_rss_link, \
    wsdot_news_description
from router.zaobao.zaobao_realtime_router import ZaobaoRealtimeRouter
from router.zaobao.zaobao_realtime_router_constants import zaobao_realtime_page_prefix, zaobao_region_general_title
from utils.config import get_router_period
from utils.router_constants import (
    language_english,
    language_chinese,
    meta_engineering_blog_router,
    cnbeta_router_path,
    zaobao_router_path_prefix,
    day_one_blog_router_path,
    earthquake_router_path,
    wsdot_news_router_path,
    embassy_router_path,
    jandan_router_path,
    reuters_news_router_path,
    sar_router_path,
    apnews_router_path,
    apnews_business_router_path,
    openai_news_router_path_prefix,
)
from router.apple_news.apple_news_router import AppleNewsRouter, AppleNewsroomRouter
from router.apple_news.apple_news_router_constants import (
    apple_developer_news_title,
    apple_developer_news_link,
    apple_developer_news_rss_link,
    apple_developer_news_description,
    apple_newsroom_title,
    apple_newsroom_link,
    apple_newsroom_rss_link,
    apple_newsroom_description,
)
from utils.router_constants import apple_news_router_path, apple_newsroom_router_path

meta_tech_blog = MetaBlog(
    router_path=meta_engineering_blog_router,
    feed_title=meta_blog_title,
    original_link=meta_blog_link,
    articles_link=meta_blog_rss_link,
    description=meta_blog_description,
    language=language_english,
    period=get_router_period("meta_blog", 30)
)

cnbeta = CnbetaRouter(
    router_path=cnbeta_router_path,
    feed_title=cnbeta_news_router_title,
    original_link=cnbeta_news_site_link,
    articles_link=cnbeta_articles_link,
    description=cnbeta_news_router_description,
    language=language_chinese,
    period=get_router_period("cnbeta", 10)
)

usgs_earthquake_report = UsgsEarthquakeRouter(
    router_path=earthquake_router_path,
    feed_title=usgs_earthquake_feed_title,
    original_link=usgs_earthquake_original_link,
    articles_link=usgs_earthquake_link,
    description=usgs_earthquake_description,
    language=language_english,
    period=get_router_period("earthquake", 15)
)

zaobao_realtime = ZaobaoRealtimeRouter(
    router_path=zaobao_router_path_prefix,
    feed_title=zaobao_region_general_title,
    articles_link=zaobao_realtime_page_prefix,
    language=language_chinese,
    period=get_router_period("zaobao", 10)
)

day_one_blog = DayOneBlogRouter(
    router_path=day_one_blog_router_path,
    feed_title=day_one_blog_router_title,
    original_link=day_one_blog_site_link,
    articles_link=day_one_blog_articles_link,
    description=day_one_blog_router_description,
    language=language_english,
    period=get_router_period("dayone", 60)
)

wsdot_news = WsdotNewsRouter(
    router_path=wsdot_news_router_path,
    feed_title=wsdot_news_title,
    original_link=wsdot_news_link,
    articles_link=wsdot_news_rss_link,
    description=wsdot_news_description,
    language=language_english,
    period=get_router_period("wsdot", 30)
)

chinese_embassy_news = ChinaEmbassyNewsRouter(
    router_path=embassy_router_path,
    feed_title=china_embassy_news_title,
    original_link=china_embassy_news_prefix,
    articles_link=china_embassy_news_prefix,
    description=china_embassy_news_description,
    language=language_chinese,
    period=get_router_period("embassy", 10)
)

jandan_news = JandanRouter(
    router_path=jandan_router_path,
    feed_title=jandan_title,
    original_link=jandan_page_prefix,
    articles_link=jandan_page_prefix,
    description=jandan_description,
    language=language_chinese,
    period=get_router_period("jandan", 60)
)

reuters_news = ReutersRouter(
    router_path=reuters_news_router_path,
    feed_title=reuters_news_name,
    original_link=reuters_site_link,
    articles_link=reuters_fetch_api_base_link,
    description=reuters_description,
    language=language_english,
    period=get_router_period("reuters", 30)
)

sony_alpha_rumors = SonyAlphaRumorsRouter(
    router_path=sar_router_path,
    feed_title=sar_name,
    original_link=sar_link,
    articles_link=sar_rss_link,
    description=sar_description,
    language=language_english,
    period=get_router_period("sar", 30)
)

apnews_top_news = ApnewsRouter(
    router_path=apnews_router_path,
    feed_title=apnews_feed_title,
    original_link=apnews_original_link,
    articles_link=apnews_articles_link,
    description=apnews_description,
    language=language_english,
    period=get_router_period("apnews_top", 15),
    default_topic="top",
    exclude_links_from_router=apnews_business_router_path,
    exclude_feed_title=apnews_business_feed_title,
)

apnews_business = ApnewsRouter(
    router_path=apnews_business_router_path,
    feed_title=apnews_business_feed_title,
    original_link=apnews_business_original_link,
    articles_link=apnews_business_articles_link,
    description=apnews_business_description,
    language=language_english,
    period=get_router_period("apnews_business", 15),
    default_topic="business",
)

openai_news = OpenAINewsRouter(
    router_path=openai_news_router_path_prefix,
    feed_title=openai_news_feed_title,
    original_link=openai_news_original_link,
    articles_link=openai_news_articles_link,
    description=openai_news_description,
    language=language_english,
    period=get_router_period("openai_news", openai_news_period // 60000),
)

apple_developer_news = AppleNewsRouter(
    router_path=apple_news_router_path,
    feed_title=apple_developer_news_title,
    original_link=apple_developer_news_link,
    articles_link=apple_developer_news_rss_link,
    description=apple_developer_news_description,
    language=language_english,
    period=get_router_period("apple_developer_news", 60),
)

apple_newsroom = AppleNewsroomRouter(
    router_path=apple_newsroom_router_path,
    feed_title=apple_newsroom_title,
    original_link=apple_newsroom_link,
    articles_link=apple_newsroom_rss_link,
    description=apple_newsroom_description,
    language=language_english,
    period=get_router_period("apple_newsroom", 60),
)
