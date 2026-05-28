import logging

from werkzeug.exceptions import abort

from application.router_dependencies import (
    apnews_business,
    apnews_top_news,
    apple_developer_news,
    apple_newsroom,
    apple_news_router_path,
    apple_newsroom_router_path,
    apnews_business_router_path,
    apnews_router_path,
    china_embassy_news_filter,
    chinese_embassy_news,
    cnbeta,
    cnbeta_router_path,
    day_one_blog,
    day_one_blog_router_path,
    earthquake_router_path,
    embassy_router_path,
    jandan_news,
    jandan_router_path,
    meta_blog_prefix,
    meta_engineering_blog_router_path,
    meta_tech_blog,
    openai_news,
    openai_news_router_path_prefix,
    reuters_news,
    reuters_news_router_path,
    sar_router_path,
    sony_alpha_rumors,
    usgs_earthquake_report,
    wsdot_news,
    wsdot_news_router_path,
    zaobao_region_parameter,
    zaobao_router_path_prefix,
    zaobao_realtime,
    title_filter,
)


def register_routes(app):
    @app.route('/')
    def hello_world():
        return "Hello there."

    @app.route(cnbeta_router_path)
    def cnbeta_router():
        return cnbeta.get_rss_xml_response()

    @app.route(day_one_blog_router_path)
    def day_one_blog_router():
        return day_one_blog.get_rss_xml_response()

    @app.route(earthquake_router_path)
    def earthquake_router():
        return usgs_earthquake_report.get_rss_xml_response()

    @app.route(embassy_router_path)
    def embassy_router():
        return chinese_embassy_news.get_rss_xml_response(parameter=None, link_filter=china_embassy_news_filter)

    @app.route(jandan_router_path)
    def jandan():
        return jandan_news.get_rss_xml_response()

    @app.route(meta_engineering_blog_router_path)
    def meta_engineering_blog_router():
        return meta_tech_blog.get_rss_xml_response(link_filter=meta_blog_prefix)

    @app.route(reuters_news_router_path + '/world')
    def reuters_world_news_router():
        return reuters_news.get_rss_xml_response(parameter={"category": "world"})

    @app.route(reuters_news_router_path + '/business')
    def reuters_business_news_router():
        return reuters_news.get_rss_xml_response(parameter={"category": "business"})

    @app.route(sar_router_path)
    def sony_alpha_rumors_router():
        return sony_alpha_rumors.get_rss_xml_response()

    @app.route(wsdot_news_router_path)
    def wsdot_router():
        return wsdot_news.get_rss_xml_response()

    @app.route(zaobao_router_path_prefix)
    @app.route(zaobao_router_path_prefix + '/<region>')
    def zaobao_router(region=None):
        """
        Support a general realtime feed and region-specific feeds.
        :param region: optional region to query
        :return: realtime news xml based on region
        """

        if region is None:
            return zaobao_realtime.get_rss_xml_response(parameter=None, title_filter=title_filter)

        if region not in zaobao_region_parameter:
            abort(404)

        parameters = {
            "region": region
        }
        return zaobao_realtime.get_rss_xml_response(parameter=parameters, title_filter=title_filter)

    @app.route(apnews_router_path)
    def apnews_router():
        return apnews_top_news.get_rss_xml_response()

    @app.route(apnews_business_router_path)
    def apnews_business_router():
        return apnews_business.get_rss_xml_response()

    @app.route(openai_news_router_path_prefix + '/<category>')
    def openai_news_router(category):
        category = category.lower()
        if category not in openai_news.VALID_CATEGORIES:
            abort(404)
        return openai_news.get_rss_xml_response(parameter={"category": category})

    @app.route(apple_news_router_path)
    def apple_developer_news_router():
        return apple_developer_news.get_rss_xml_response()

    @app.route(apple_newsroom_router_path)
    def apple_newsroom_router():
        return apple_newsroom.get_rss_xml_response()
