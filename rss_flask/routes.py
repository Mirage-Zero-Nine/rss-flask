import logging

from router.embassy.china_embassy_news_constants import china_embassy_news_filter
from router.meta_blog.meta_tech_blog_router_constants import meta_blog_prefix
from router.reuters.reuters_constants import is_valid_reuters_parameter
from router.zaobao.zaobao_realtime_router_constants import (
    title_filter,
    zaobao_region_parameter,
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
from utils.log_context import log_with_context, router_log_context
from werkzeug.exceptions import abort


def register_routes(app, routers):
    @app.route("/")
    def hello_world():
        return "Hello there."

    simple_routes = (
        (CNBETA_ROUTE_PATH, "cnbeta_router", routers["cnbeta"], {}),
        (DAY_ONE_BLOG_ROUTE_PATH, "day_one_blog_router", routers["day_one_blog"], {}),
        (EARTHQUAKE_ROUTE_PATH, "earthquake_router", routers["usgs_earthquake_report"], {}),
        (
            EMBASSY_ROUTE_PATH,
            "embassy_router",
            routers["chinese_embassy_news"],
            {"link_filter": china_embassy_news_filter},
        ),
        (JANDAN_ROUTE_PATH, "jandan_router", routers["jandan_news"], {}),
        (
            META_ENGINEERING_BLOG_ROUTE_PATH,
            "meta_engineering_blog_router",
            routers["meta_tech_blog"],
            {"link_filter": meta_blog_prefix},
        ),
        (NBC_NEWS_ROUTE_PATH, "nbc_news_router", routers["nbc_news"], {}),
        (SAR_ROUTE_PATH, "sony_alpha_rumors_router", routers["sony_alpha_rumors"], {}),
        (THE_VERGE_ROUTE_PATH, "the_verge_router", routers["the_verge"], {}),
        (
            TWITTER_ENGINEERING_BLOG_ROUTE_PATH,
            "twitter_engineering_blog_router",
            routers["twitter_engineering_blog"],
            {},
        ),
        (WSDOT_NEWS_ROUTE_PATH, "wsdot_router", routers["wsdot_news"], {}),
        (ZHIHU_ROUTE_PATH, "zhihu_router", routers["zhihu_daily"], {}),
    )

    for path, endpoint_name, router, response_kwargs in simple_routes:
        app.add_url_rule(
            path,
            endpoint=endpoint_name,
            view_func=_build_router_view(router, **response_kwargs),
        )

    @app.route(REUTERS_NEWS_ROUTE_PATH + "/<category>")
    @app.route(REUTERS_NEWS_ROUTE_PATH + "/<category>/<string:topic>")
    @app.route(REUTERS_NEWS_ROUTE_PATH + "/<category>/<string:topic>/<int:limit>")
    def reuters_news_router(category, topic=None, limit=20):
        if is_valid_reuters_parameter(category, topic) is False:
            abort(404)

        parameters = {
            "category": category,
            "topic": topic,
            "limit": limit,
        }
        router = routers["reuters_news"]
        with router_log_context(router.router_name, router.router_path, "route-request"):
            log_with_context(
                logging.INFO,
                "route_request category=%s topic=%s limit=%s",
                category,
                topic,
                limit,
            )
            return router.get_rss_xml_response(parameter=parameters)

    @app.route(ZAOBAO_ROUTE_PATH_PREFIX + "/<region>")
    def zaobao_router(region):
        if region not in zaobao_region_parameter:
            abort(404)

        return routers["zaobao_realtime"].get_rss_xml_response(
            parameter={"region": region},
            title_filter=title_filter,
        )


def _build_router_view(router, **response_kwargs):
    def view():
        return router.get_rss_xml_response(**response_kwargs)

    return view
