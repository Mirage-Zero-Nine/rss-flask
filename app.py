import logging
import os
import sys

LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = '%(asctime)s %(levelname)s %(name)s: %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'application.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)

from flask import Flask
from router.embassy.china_embassy_news_constants import china_embassy_news_filter
from router.meta_blog.meta_tech_blog_router_constants import meta_blog_prefix
from router.reuters.reuters_constants import is_valid_reuters_parameter
from router.zaobao.zaobao_realtime_router_constants import zaobao_region_parameter, title_filter
from router_objects import meta_tech_blog, cnbeta, usgs_earthquake_report, \
    zaobao_realtime, day_one_blog, wsdot_news, chinese_embassy_news, \
    jandan_news, reuters_news, sony_alpha_rumors
from utils.router_constants import wsdot_news_router_path, \
    meta_engineering_blog_router, \
    jandan_router_path, earthquake_router_path, embassy_router_path, \
    day_one_blog_router_path, cnbeta_router_path, zaobao_router_path_prefix, \
    reuters_news_router_path, sar_router_path
from utils.scheduler import router_refresh_job_scheduler
from werkzeug.exceptions import abort

app = Flask(__name__)
app.logger.setLevel(logging.INFO)


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


router_refresh_job_scheduler(app)

if __name__ == '__main__':
    app.run()
