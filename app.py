import logging

from flask import Flask
from router.embassy.china_embassy_news_constants import china_embassy_news_filter
from router.meta_blog.meta_tech_blog_router_constants import meta_blog_prefix
from router.reuters.reuters_constants import is_valid_reuters_parameter
from router.zaobao.zaobao_realtime_router_constants import zaobao_region_parameter, title_filter
from router_objects import meta_tech_blog, cnbeta, the_verge, usgs_earthquake_report, twitter_engineering_blog, \
    telegram_wechat_channel, zaobao_realtime, day_one_blog, nbc_news, wsdot_news, zhihu_daily, chinese_embassy_news, \
    jandan_news, reuters_news
from utils.router_constants import zhihu_router_path, wsdot_news_router_path, \
    twitter_engineering_blog_router_path, the_verge_router_path, meta_engineering_blog_router, \
    telegram_wechat_router_path, jandan_router_path, earthquake_router_path, embassy_router_path, \
    day_one_blog_router_path, cnbeta_router_path, zaobao_router_path_prefix, nbc_news_router_path, \
    reuters_news_router_path
from utils.scheduler import router_refresh_job_scheduler
from werkzeug.exceptions import abort

app = Flask(__name__)
app.logger.setLevel(logging.INFO)
logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.INFO)


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


@app.route(meta_engineering_blog_router)
def meta_engineering_blog_router():
    return meta_tech_blog.get_rss_xml_response(link_filter=meta_blog_prefix)


@app.route(nbc_news_router_path)
def nbc_news_router():
    return nbc_news.get_rss_xml_response()


@app.route(reuters_news_router_path + '/<category>')
@app.route(reuters_news_router_path + '/<category>/<string:topic>')
@app.route(reuters_news_router_path + '/<category>/<string:topic>/<int:limit>')
def reuters_news_router(category, topic=None, limit=20):
    """
    Reuters news.
    :param category: required for the Reuters API
    :param topic: optional for the Reuters API
    :param limit: amount of articles retrieved from API, 20 maximum
    :return: RSS XML
    """

    if is_valid_reuters_parameter(category, topic) is False:
        abort(404)

    parameters = {
        "category": category,
        "topic": topic,
        "limit": limit
    }

    logging.info(f"category: {category}, topic:{topic}")
    return reuters_news.get_rss_xml_response(parameter=parameters)


@app.route(telegram_wechat_router_path)
def telegram_wechat_router():
    xml_response = telegram_wechat_channel.get_rss_xml_response()
    return xml_response


@app.route(the_verge_router_path)
def the_verge_router():
    return the_verge.get_rss_xml_response()


@app.route(twitter_engineering_blog_router_path)
def twitter_engineering_blog_router():
    return twitter_engineering_blog.get_rss_xml_response()


@app.route(wsdot_news_router_path)
def wsdot_router():
    return wsdot_news.get_rss_xml_response()


@app.route(zaobao_router_path_prefix + '/<region>')
def zaobao_router(region):
    """
    Currently support two regions: `china` and `world`.
    :param region: region to query
    :return: realtime news xml based on region
    """

    # region is a required argument
    if region not in zaobao_region_parameter:
        abort(404)

    parameters = {
        "region": region
    }
    return zaobao_realtime.get_rss_xml_response(parameter=parameters, title_filter=title_filter)


@app.route(zhihu_router_path)
def zhihu_router():
    return zhihu_daily.get_rss_xml_response()


router_refresh_job_scheduler(app)

if __name__ == '__main__':
    app.run()
