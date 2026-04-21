from dataclasses import dataclass
from typing import Optional

from router.cnbeta.cnbeta_router import CnbetaRouter
from router.cnbeta.cnbeta_router_constants import (
    cnbeta_articles_link,
    cnbeta_news_router_description,
    cnbeta_news_router_title,
    cnbeta_news_site_link,
    cnbeta_period,
)
from router.dayone.day_one_blog_constants import (
    day_one_blog_articles_link,
    day_one_blog_query_period,
    day_one_blog_router_description,
    day_one_blog_router_title,
    day_one_blog_site_link,
)
from router.dayone.day_one_blog_router import DayOneBlogRouter
from router.earthquake.usgs_earthquake_router import UsgsEarthquakeRouter
from router.earthquake.usgs_earthquake_router_constants import (
    usgs_earthquake_description,
    usgs_earthquake_feed_title,
    usgs_earthquake_link,
    usgs_earthquake_original_link,
    usgs_earthquake_query_period,
)
from router.embassy.china_embassy_news import ChinaEmbassyNewsRouter
from router.embassy.china_embassy_news_constants import (
    china_embassy_news_description,
    china_embassy_news_filter,
    china_embassy_news_period,
    china_embassy_news_prefix,
    china_embassy_news_title,
)
from router.jandan.jandan_constant import (
    jandan_description,
    jandan_page_prefix,
    jandan_query_period,
    jandan_title,
)
from router.jandan.jandan_router import JandanRouter
from router.meta_blog.meta_tech_blog_router import MetaBlog
from router.meta_blog.meta_tech_blog_router_constants import (
    meta_blog_description,
    meta_blog_link,
    meta_blog_period,
    meta_blog_prefix,
    meta_blog_rss_link,
    meta_blog_title,
)
from router.nbc_news.nbc_news_router import NbcNewsRouter
from router.nbc_news.nbc_news_router_constants import (
    nbc_news_description,
    nbc_news_original_link,
    nbc_news_period,
    nbc_news_rss_link,
    nbc_news_title,
)
from router.reuters.reuters_constants import (
    reuters_description,
    reuters_fetch_api_base_link,
    reuters_news_name,
    reuters_period,
    reuters_site_link,
)
from router.reuters.reuters_router import ReutersRouter
from router.sony_alpha_rumor.sony_alpha_rumor_router import SonyAlphaRumorsRouter
from router.sony_alpha_rumor.sony_alpha_rumor_router_constants import (
    sar_description,
    sar_link,
    sar_name,
    sar_query_period,
    sar_rss_link,
)
from router.the_verge.the_verge_constants import (
    the_verge_archive,
    the_verge_description,
    the_verge_prefix,
    the_verge_title,
)
from router.the_verge.the_verge_router import TheVergeRouter
from router.twitter_engineering_blog.twitter_engineering_blog_router import (
    TwitterEngineeringBlogRouter,
)
from router.twitter_engineering_blog.twitter_engineering_blog_router_constants import (
    twitter_engineering_blog_description,
    twitter_engineering_blog_original_link,
    twitter_engineering_blog_period,
    twitter_engineering_blog_rss_link,
    twitter_engineering_blog_title,
)
from router.wsdot.wsdot_news_router import WsdotNewsRouter
from router.wsdot.wsdot_news_router_constant import (
    wsdot_news_description,
    wsdot_news_link,
    wsdot_news_period,
    wsdot_news_title,
)
from router.zaobao.zaobao_realtime_router import ZaobaoRealtimeRouter
from router.zaobao.zaobao_realtime_router_constants import (
    title_filter as zaobao_title_filter,
    zaobao_query_period,
    zaobao_region_general_title,
    zaobao_realtime_page_prefix,
)
from router.zhihu.zhihu_daily_router import ZhihuDailyRouter
from router.zhihu.zhihu_daily_router_constants import (
    zhihu_daily_description,
    zhihu_daily_link,
    zhihu_daily_title,
    zhihu_query_period,
)
from rss_flask.route_config import (
    CNBETA_ROUTE_PATH,
    DAY_ONE_BLOG_ROUTE_PATH,
    EARTHQUAKE_ROUTE_PATH,
    EMBASSY_ROUTE_PATH,
    JANDAN_ROUTE_PATH,
    META_ENGINEERING_BLOG_ROUTE_PATH,
    NBC_NEWS_ROUTE_PATH,
    REUTERS_NEWS_ROUTE_PATH,
    SAR_ROUTE_PATH,
    THE_VERGE_ROUTE_PATH,
    TWITTER_ENGINEERING_BLOG_ROUTE_PATH,
    WSDOT_NEWS_ROUTE_PATH,
    ZAOBAO_ROUTE_PATH_PREFIX,
    ZHIHU_ROUTE_PATH,
)
from rss_flask.settings import LANGUAGE_CHINESE, LANGUAGE_ENGLISH


@dataclass(frozen=True)
class RouterDefinition:
    key: str
    router_cls: type
    router_path: str
    feed_title: str
    original_link: Optional[str] = None
    articles_link: Optional[str] = None
    description: str = ""
    language: str = ""
    period: int = 1000
    scheduler_interval_minutes: Optional[int] = None

    def build(self):
        return self.router_cls(
            router_path=self.router_path,
            feed_title=self.feed_title,
            original_link=self.original_link,
            articles_link=self.articles_link,
            description=self.description,
            language=self.language,
            period=self.period,
        )

    @property
    def resolved_scheduler_interval_minutes(self):
        if self.scheduler_interval_minutes is not None:
            return self.scheduler_interval_minutes
        return max(1, int(self.period / 60000))


@dataclass(frozen=True)
class ScheduledRefreshDefinition:
    job_id: str
    router_key: str
    interval_minutes: int
    parameter: Optional[dict] = None
    link_filter: Optional[str] = None
    title_filter: Optional[str] = None


ROUTER_DEFINITIONS = (
    RouterDefinition(
        key="meta_tech_blog",
        router_cls=MetaBlog,
        router_path=META_ENGINEERING_BLOG_ROUTE_PATH,
        feed_title=meta_blog_title,
        original_link=meta_blog_link,
        articles_link=meta_blog_rss_link,
        description=meta_blog_description,
        language=LANGUAGE_ENGLISH,
        period=meta_blog_period,
    ),
    RouterDefinition(
        key="cnbeta",
        router_cls=CnbetaRouter,
        router_path=CNBETA_ROUTE_PATH,
        feed_title=cnbeta_news_router_title,
        original_link=cnbeta_news_site_link,
        articles_link=cnbeta_articles_link,
        description=cnbeta_news_router_description,
        language=LANGUAGE_CHINESE,
        period=cnbeta_period,
    ),
    RouterDefinition(
        key="the_verge",
        router_cls=TheVergeRouter,
        router_path=THE_VERGE_ROUTE_PATH,
        feed_title=the_verge_title,
        original_link=the_verge_prefix,
        articles_link=the_verge_archive,
        description=the_verge_description,
        language=LANGUAGE_ENGLISH,
        period=cnbeta_period,
    ),
    RouterDefinition(
        key="usgs_earthquake_report",
        router_cls=UsgsEarthquakeRouter,
        router_path=EARTHQUAKE_ROUTE_PATH,
        feed_title=usgs_earthquake_feed_title,
        original_link=usgs_earthquake_original_link,
        articles_link=usgs_earthquake_link,
        description=usgs_earthquake_description,
        language=LANGUAGE_ENGLISH,
        period=usgs_earthquake_query_period,
    ),
    RouterDefinition(
        key="twitter_engineering_blog",
        router_cls=TwitterEngineeringBlogRouter,
        router_path=TWITTER_ENGINEERING_BLOG_ROUTE_PATH,
        feed_title=twitter_engineering_blog_title,
        original_link=twitter_engineering_blog_original_link,
        articles_link=twitter_engineering_blog_rss_link,
        description=twitter_engineering_blog_description,
        language=LANGUAGE_ENGLISH,
        period=twitter_engineering_blog_period,
    ),
    RouterDefinition(
        key="zaobao_realtime",
        router_cls=ZaobaoRealtimeRouter,
        router_path=ZAOBAO_ROUTE_PATH_PREFIX,
        feed_title=zaobao_region_general_title,
        articles_link=zaobao_realtime_page_prefix,
        language=LANGUAGE_CHINESE,
        period=zaobao_query_period,
    ),
    RouterDefinition(
        key="day_one_blog",
        router_cls=DayOneBlogRouter,
        router_path=DAY_ONE_BLOG_ROUTE_PATH,
        feed_title=day_one_blog_router_title,
        original_link=day_one_blog_site_link,
        articles_link=day_one_blog_articles_link,
        description=day_one_blog_router_description,
        language=LANGUAGE_ENGLISH,
        period=day_one_blog_query_period,
    ),
    RouterDefinition(
        key="nbc_news",
        router_cls=NbcNewsRouter,
        router_path=NBC_NEWS_ROUTE_PATH,
        feed_title=nbc_news_title,
        original_link=nbc_news_original_link,
        articles_link=nbc_news_rss_link,
        description=nbc_news_description,
        language=LANGUAGE_ENGLISH,
        period=nbc_news_period,
    ),
    RouterDefinition(
        key="wsdot_news",
        router_cls=WsdotNewsRouter,
        router_path=WSDOT_NEWS_ROUTE_PATH,
        feed_title=wsdot_news_title,
        original_link=wsdot_news_link,
        articles_link=wsdot_news_link,
        description=wsdot_news_description,
        language=LANGUAGE_ENGLISH,
        period=wsdot_news_period,
    ),
    RouterDefinition(
        key="zhihu_daily",
        router_cls=ZhihuDailyRouter,
        router_path=ZHIHU_ROUTE_PATH,
        feed_title=zhihu_daily_title,
        original_link=zhihu_daily_link,
        articles_link=zhihu_daily_link,
        description=zhihu_daily_description,
        language=LANGUAGE_CHINESE,
        period=zhihu_query_period,
    ),
    RouterDefinition(
        key="chinese_embassy_news",
        router_cls=ChinaEmbassyNewsRouter,
        router_path=EMBASSY_ROUTE_PATH,
        feed_title=china_embassy_news_title,
        original_link=china_embassy_news_prefix,
        articles_link=china_embassy_news_prefix,
        description=china_embassy_news_description,
        language=LANGUAGE_CHINESE,
        period=china_embassy_news_period,
    ),
    RouterDefinition(
        key="jandan_news",
        router_cls=JandanRouter,
        router_path=JANDAN_ROUTE_PATH,
        feed_title=jandan_title,
        original_link=jandan_page_prefix,
        articles_link=jandan_page_prefix,
        description=jandan_description,
        language=LANGUAGE_CHINESE,
        period=jandan_query_period,
    ),
    RouterDefinition(
        key="reuters_news",
        router_cls=ReutersRouter,
        router_path=REUTERS_NEWS_ROUTE_PATH,
        feed_title=reuters_news_name,
        original_link=reuters_site_link,
        articles_link=reuters_fetch_api_base_link,
        description=reuters_description,
        language=LANGUAGE_ENGLISH,
        period=reuters_period,
    ),
    RouterDefinition(
        key="sony_alpha_rumors",
        router_cls=SonyAlphaRumorsRouter,
        router_path=SAR_ROUTE_PATH,
        feed_title=sar_name,
        original_link=sar_link,
        articles_link=sar_rss_link,
        description=sar_description,
        language=LANGUAGE_ENGLISH,
        period=sar_query_period,
    ),
)


def build_router_registry():
    return {definition.key: definition.build() for definition in ROUTER_DEFINITIONS}


def build_scheduled_refresh_definitions():
    by_key = {definition.key: definition for definition in ROUTER_DEFINITIONS}
    return (
        ScheduledRefreshDefinition(
            job_id="cnbeta",
            router_key="cnbeta",
            interval_minutes=by_key["cnbeta"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="day_one_blog",
            router_key="day_one_blog",
            interval_minutes=by_key["day_one_blog"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="earthquake",
            router_key="usgs_earthquake_report",
            interval_minutes=by_key["usgs_earthquake_report"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="embassy",
            router_key="chinese_embassy_news",
            interval_minutes=by_key["chinese_embassy_news"].resolved_scheduler_interval_minutes,
            link_filter=china_embassy_news_filter,
        ),
        ScheduledRefreshDefinition(
            job_id="jandan",
            router_key="jandan_news",
            interval_minutes=by_key["jandan_news"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="meta_blog",
            router_key="meta_tech_blog",
            interval_minutes=by_key["meta_tech_blog"].resolved_scheduler_interval_minutes,
            link_filter=meta_blog_prefix,
        ),
        ScheduledRefreshDefinition(
            job_id="nbc_news",
            router_key="nbc_news",
            interval_minutes=by_key["nbc_news"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="reuters_world",
            router_key="reuters_news",
            interval_minutes=by_key["reuters_news"].resolved_scheduler_interval_minutes,
            parameter={"category": "world", "topic": None, "limit": 20},
        ),
        ScheduledRefreshDefinition(
            job_id="sar",
            router_key="sony_alpha_rumors",
            interval_minutes=by_key["sony_alpha_rumors"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="the_verge",
            router_key="the_verge",
            interval_minutes=by_key["the_verge"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="twitter_blog",
            router_key="twitter_engineering_blog",
            interval_minutes=by_key["twitter_engineering_blog"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="wsdot",
            router_key="wsdot_news",
            interval_minutes=by_key["wsdot_news"].resolved_scheduler_interval_minutes,
        ),
        ScheduledRefreshDefinition(
            job_id="zaobao_china",
            router_key="zaobao_realtime",
            interval_minutes=by_key["zaobao_realtime"].resolved_scheduler_interval_minutes,
            parameter={"region": "china"},
            title_filter=zaobao_title_filter,
        ),
        ScheduledRefreshDefinition(
            job_id="zaobao_world",
            router_key="zaobao_realtime",
            interval_minutes=by_key["zaobao_realtime"].resolved_scheduler_interval_minutes,
            parameter={"region": "world"},
            title_filter=zaobao_title_filter,
        ),
        ScheduledRefreshDefinition(
            job_id="zhihu",
            router_key="zhihu_daily",
            interval_minutes=by_key["zhihu_daily"].resolved_scheduler_interval_minutes,
        ),
    )
