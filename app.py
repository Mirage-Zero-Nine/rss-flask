import logging

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

from router.zaobao import zaobao_realtime_router
from router.dayone import dayone_router
from router.jandan import jandan_router
from router.currency import currency_router
from router.earthquake import usgs_earthquake_router
from router.zhihu import zhihu_daily_router
from router.embassy import china_embassy_router
from router.telegram import wechat_channel_router
from router.wsdot import wsdot_news_router
from router.the_verge import the_verge_router
from router.cnbeta import cnbeta_router

from utils.router_constants import routes_to_call, refresh_period_in_minutes

app = Flask(__name__)

# file path started from app.py
with open('authentication.yaml') as f:
    # use safe_load instead load
    config = yaml.safe_load(f)


@app.route('/')
def hello_world():
    return "Hello there."


@app.route('/cnbeta')
def cnbeta():
    xml_response = cnbeta_router.get_rss_xml_response()
    return xml_response


@app.route('/currency/<currency_name>')
def currency(currency_name):
    xml_response = currency_router.get_rss_xml_response(currency_name)
    return xml_response


@app.route('/dayone')
def dayone():
    xml_response = dayone_router.get_rss_xml_response()
    return xml_response


@app.route('/earthquake')
def earthquake():
    xml_response = usgs_earthquake_router.get_rss_xml_response()
    return xml_response


@app.route('/embassy')
def embassy():
    xml_response = china_embassy_router.get_rss_xml_response()
    return xml_response


@app.route('/jandan')
def jandan():
    return jandan_router.get_rss_xml_response()


@app.route('/telegram/wechat')
def telegram_wechat():
    xml_response = wechat_channel_router.get_rss_xml_response(config)
    return xml_response


@app.route('/theverge')
def the_verge():
    xml_response = the_verge_router.get_rss_xml_response()
    return xml_response


@app.route('/wsdot/news')
def wsdot():
    xml_response = wsdot_news_router.get_rss_xml_response()
    return xml_response


@app.route('/zaobao/realtime/<region>')
def zaobao(region):
    """
    Currently support two regions: `china` and `world`.
    :param region: region to query
    :return: realtime news xml based on region
    """
    xml_response = zaobao_realtime_router.get_rss_xml_response(region)
    return xml_response


@app.route('/zhihu/daily')
def zhihu():
    xml_response = zhihu_daily_router.get_rss_xml_response()
    return xml_response


# Create a scheduler
scheduler = BackgroundScheduler()
scheduler.start()


def call_route(router_path):
    with app.test_request_context(router_path):
        logging.info(f"scheduler run with path: {router_path}")
        app.dispatch_request()


for r in routes_to_call:
    logging.info(f"Router {r} added to scheduler job.")
    scheduler.add_job(call_route, 'interval', minutes=refresh_period_in_minutes, args=[r])

if __name__ == '__main__':
    app.run()
