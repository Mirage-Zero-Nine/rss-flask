import logging

import yaml
from flask import Flask

from router.dayone import dayone_router
from router.embassy import china_embassy_router
from router.jandan import jandan_router
from router.meta_blog.meta_router_constants import meta_blog_prefix
from router.telegram import wechat_channel_router
from router.wsdot import wsdot_news_router
from router.zaobao import zaobao_realtime_router
from router.zhihu import zhihu_daily_router
from router_objects import meta_blog, cnbeta, the_verge, usgs_earthquake_report, currency_exchange_price, \
    twitter_engineering_blog
from utils.router_constants import zhihu_router_path, wsdot_news_router_path, \
    twitter_engineering_blog_router_path, the_verge_router_path, meta_engineering_blog_router, \
    telegram_wechat_router_path, jandan_router_path, earthquake_router_path, embassy_router_path, \
    dayone_blog_router_path, cnbeta_router_path, zaobao_router_path_prefix, currency_exchange_price_router_path
from utils.scheduler import router_refresh_job_scheduler

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# file path started from app.py
with open('config.yml') as f:
    # use safe_load instead load
    config = yaml.safe_load(f)


@app.route('/')
def hello_world():
    return "Hello there."


@app.route(cnbeta_router_path)
def cnbeta_router():
    return cnbeta.get_rss_xml_response()


@app.route(currency_exchange_price_router_path + '<currency_name>')
def currency_exchange_price_router(currency_name):
    return currency_exchange_price.get_rss_xml_response(parameter=currency_name)


@app.route(dayone_blog_router_path)
def dayone_blog_router():
    xml_response = dayone_router.get_rss_xml_response()
    return xml_response


@app.route(earthquake_router_path)
def earthquake_router():
    return usgs_earthquake_report.get_rss_xml_response()


@app.route(embassy_router_path)
def embassy_router():
    xml_response = china_embassy_router.get_rss_xml_response()
    return xml_response


@app.route(jandan_router_path)
def jandan():
    return jandan_router.get_rss_xml_response()


@app.route(meta_engineering_blog_router)
def meta_engineering_blog_router():
    return meta_blog.get_rss_xml_response(link_filter=meta_blog_prefix)


@app.route(telegram_wechat_router_path)
def telegram_wechat_router():
    xml_response = wechat_channel_router.get_rss_xml_response(config)
    return xml_response


@app.route(the_verge_router_path)
def the_verge_router():
    return the_verge.get_rss_xml_response()


@app.route(twitter_engineering_blog_router_path)
def twitter_engineering_blog_router():
    return twitter_engineering_blog.get_rss_xml_response()


@app.route(wsdot_news_router_path)
def wsdot_router():
    xml_response = wsdot_news_router.get_rss_xml_response()
    return xml_response


@app.route(zaobao_router_path_prefix + '<region>')
def zaobao_router(region):
    """
    Currently support two regions: `china` and `world`.
    :param region: region to query
    :return: realtime news xml based on region
    """
    xml_response = zaobao_realtime_router.get_rss_xml_response(region)
    return xml_response


@app.route(zhihu_router_path)
def zhihu_router():
    xml_response = zhihu_daily_router.get_rss_xml_response()
    return xml_response


router_refresh_job_scheduler(app)

if __name__ == '__main__':
    app.run()
