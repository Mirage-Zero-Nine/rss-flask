from dataclasses import dataclass, field

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
from router.wsdot.wsdot_news_router import WsdotNewsRouter
from router.wsdot.wsdot_news_router_constant import (
    wsdot_news_description,
    wsdot_news_link,
    wsdot_news_period,
    wsdot_news_title,
)
from router.zaobao.zaobao_realtime_router import ZaobaoRealtimeRouter
from router.zaobao.zaobao_realtime_router_constants import (
    title_filter,
    zaobao_query_period,
    zaobao_realtime_page_prefix,
    zaobao_region_general_title,
)
from utils.router_constants import (
    cnbeta_router_path,
    day_one_blog_router_path,
    embassy_router_path,
    earthquake_router_path,
    jandan_router_path,
    language_chinese,
    language_english,
    meta_engineering_blog_router,
    reuters_news_router_path,
    sar_router_path,
    wsdot_news_router_path,
    zaobao_router_path_prefix,
)


@dataclass(frozen=True)
class FeedDefinition:
    name: str
    router_cls: type
    router_path: str
    feed_title: str
    original_link: str = ""
    articles_link: str = ""
    description: str = ""
    language: str = ""
    period: int = 1000
    endpoint: str | None = None
    response_kwargs: dict = field(default_factory=dict)
    scheduled_paths: tuple[str, ...] = ()

    def build_router(self):
        return self.router_cls(
            router_path=self.router_path,
            feed_title=self.feed_title,
            original_link=self.original_link,
            articles_link=self.articles_link,
            description=self.description,
            language=self.language,
            period=self.period,
        )


@dataclass(frozen=True)
class StaticFeedRoute:
    endpoint: str
    path: str
    router: object
    response_kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RouteRule:
    rule: str
    endpoint: str
    defaults: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DynamicFeedRoute:
    handler_type: str
    router: object
    rules: tuple[RouteRule, ...]


FEED_DEFINITIONS = (
    FeedDefinition(
        name="meta_tech_blog",
        router_cls=MetaBlog,
        router_path=meta_engineering_blog_router,
        feed_title=meta_blog_title,
        original_link=meta_blog_link,
        articles_link=meta_blog_rss_link,
        description=meta_blog_description,
        language=language_english,
        period=meta_blog_period,
        endpoint="meta_engineering_blog_router",
        response_kwargs={"link_filter": meta_blog_prefix},
        scheduled_paths=(meta_engineering_blog_router,),
    ),
    FeedDefinition(
        name="cnbeta",
        router_cls=CnbetaRouter,
        router_path=cnbeta_router_path,
        feed_title=cnbeta_news_router_title,
        original_link=cnbeta_news_site_link,
        articles_link=cnbeta_articles_link,
        description=cnbeta_news_router_description,
        language=language_chinese,
        period=cnbeta_period,
        endpoint="cnbeta_router",
        scheduled_paths=(cnbeta_router_path,),
    ),
    FeedDefinition(
        name="usgs_earthquake_report",
        router_cls=UsgsEarthquakeRouter,
        router_path=earthquake_router_path,
        feed_title=usgs_earthquake_feed_title,
        original_link=usgs_earthquake_original_link,
        articles_link=usgs_earthquake_link,
        description=usgs_earthquake_description,
        language=language_english,
        period=usgs_earthquake_query_period,
        endpoint="earthquake_router",
        scheduled_paths=(earthquake_router_path,),
    ),
    FeedDefinition(
        name="zaobao_realtime",
        router_cls=ZaobaoRealtimeRouter,
        router_path=zaobao_router_path_prefix,
        feed_title=zaobao_region_general_title,
        articles_link=zaobao_realtime_page_prefix,
        language=language_chinese,
        period=zaobao_query_period,
        scheduled_paths=(
            zaobao_router_path_prefix + "/china",
            zaobao_router_path_prefix + "/world",
        ),
    ),
    FeedDefinition(
        name="day_one_blog",
        router_cls=DayOneBlogRouter,
        router_path=day_one_blog_router_path,
        feed_title=day_one_blog_router_title,
        original_link=day_one_blog_site_link,
        articles_link=day_one_blog_articles_link,
        description=day_one_blog_router_description,
        language=language_english,
        period=day_one_blog_query_period,
        endpoint="day_one_blog_router",
        scheduled_paths=(day_one_blog_router_path,),
    ),
    FeedDefinition(
        name="wsdot_news",
        router_cls=WsdotNewsRouter,
        router_path=wsdot_news_router_path,
        feed_title=wsdot_news_title,
        original_link=wsdot_news_link,
        articles_link=wsdot_news_link,
        description=wsdot_news_description,
        language=language_english,
        period=wsdot_news_period,
        endpoint="wsdot_router",
        scheduled_paths=(wsdot_news_router_path,),
    ),
    FeedDefinition(
        name="chinese_embassy_news",
        router_cls=ChinaEmbassyNewsRouter,
        router_path=embassy_router_path,
        feed_title=china_embassy_news_title,
        original_link=china_embassy_news_prefix,
        articles_link=china_embassy_news_prefix,
        description=china_embassy_news_description,
        language=language_chinese,
        period=china_embassy_news_period,
        endpoint="embassy_router",
        response_kwargs={"parameter": None, "link_filter": china_embassy_news_filter},
        scheduled_paths=(embassy_router_path,),
    ),
    FeedDefinition(
        name="jandan_news",
        router_cls=JandanRouter,
        router_path=jandan_router_path,
        feed_title=jandan_title,
        original_link=jandan_page_prefix,
        articles_link=jandan_page_prefix,
        description=jandan_description,
        language=language_chinese,
        period=jandan_query_period,
        endpoint="jandan_router",
        scheduled_paths=(jandan_router_path,),
    ),
    FeedDefinition(
        name="reuters_news",
        router_cls=ReutersRouter,
        router_path=reuters_news_router_path,
        feed_title=reuters_news_name,
        original_link=reuters_site_link,
        articles_link=reuters_fetch_api_base_link,
        description=reuters_description,
        language=language_english,
        period=reuters_period,
        scheduled_paths=(reuters_news_router_path + "/world",),
    ),
    FeedDefinition(
        name="sony_alpha_rumors",
        router_cls=SonyAlphaRumorsRouter,
        router_path=sar_router_path,
        feed_title=sar_name,
        original_link=sar_link,
        articles_link=sar_rss_link,
        description=sar_description,
        language=language_english,
        period=sar_query_period,
        endpoint="sony_alpha_rumors_router",
        scheduled_paths=(sar_router_path,),
    ),
)

ROUTERS_BY_NAME = {definition.name: definition.build_router() for definition in FEED_DEFINITIONS}

meta_tech_blog = ROUTERS_BY_NAME["meta_tech_blog"]
cnbeta = ROUTERS_BY_NAME["cnbeta"]
usgs_earthquake_report = ROUTERS_BY_NAME["usgs_earthquake_report"]
zaobao_realtime = ROUTERS_BY_NAME["zaobao_realtime"]
day_one_blog = ROUTERS_BY_NAME["day_one_blog"]
wsdot_news = ROUTERS_BY_NAME["wsdot_news"]
chinese_embassy_news = ROUTERS_BY_NAME["chinese_embassy_news"]
jandan_news = ROUTERS_BY_NAME["jandan_news"]
reuters_news = ROUTERS_BY_NAME["reuters_news"]
sony_alpha_rumors = ROUTERS_BY_NAME["sony_alpha_rumors"]

STATIC_FEED_ROUTES = [
    StaticFeedRoute(
        endpoint=definition.endpoint,
        path=definition.router_path,
        router=ROUTERS_BY_NAME[definition.name],
        response_kwargs=definition.response_kwargs,
    )
    for definition in FEED_DEFINITIONS
    if definition.endpoint is not None
]

DYNAMIC_FEED_ROUTES = (
    DynamicFeedRoute(
        handler_type="reuters",
        router=reuters_news,
        rules=(
            RouteRule(
                rule=reuters_news_router_path + "/<category>",
                endpoint="reuters_news_router",
                defaults={"topic": None, "limit": 20},
            ),
            RouteRule(
                rule=reuters_news_router_path + "/<category>/<string:topic>",
                endpoint="reuters_news_router_with_topic",
                defaults={"limit": 20},
            ),
            RouteRule(
                rule=reuters_news_router_path + "/<category>/<string:topic>/<int:limit>",
                endpoint="reuters_news_router_with_topic_and_limit",
            ),
        ),
    ),
    DynamicFeedRoute(
        handler_type="zaobao",
        router=zaobao_realtime,
        rules=(
            RouteRule(
                rule=zaobao_router_path_prefix,
                endpoint="zaobao_router",
                defaults={"region": None},
            ),
            RouteRule(
                rule=zaobao_router_path_prefix + "/<region>",
                endpoint="zaobao_router_with_region",
            ),
        ),
    ),
)

SCHEDULED_ROUTE_PATHS = [
    path
    for definition in FEED_DEFINITIONS
    for path in definition.scheduled_paths
]

ZAOBAO_TITLE_FILTER = title_filter
