import logging

from flask import Flask
from werkzeug.exceptions import abort

from router.embassy import china_embassy_router
from router.jandan import jandan_router
from router.meta_blog.meta_router_constants import meta_blog_prefix
from router.wsdot import wsdot_news_router
from router.zaobao.zaobao_realtime_router_constants import zaobao_region_parameter, title_filter
from router.zhihu import zhihu_daily_router
from router_objects import meta_blog, cnbeta, the_verge, usgs_earthquake_report, twitter_engineering_blog, \
    telegram_wechat_channel, zaobao_realtime, day_one_blog
from utils.router_constants import zhihu_router_path, wsdot_news_router_path, \
    twitter_engineering_blog_router_path, the_verge_router_path, meta_engineering_blog_router, \
    telegram_wechat_router_path, jandan_router_path, earthquake_router_path, embassy_router_path, \
    day_one_blog_router_path, cnbeta_router_path, zaobao_router_path_prefix
from utils.scheduler import router_refresh_job_scheduler

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
    xml_response = wsdot_news_router.get_rss_xml_response()
    return xml_response


@app.route(zaobao_router_path_prefix + '/<region>')
def zaobao_router(region):
    """
    Currently support two regions: `china` and `world`.
    :param region: region to query
    :return: realtime news xml based on region
    """
    if region not in zaobao_region_parameter:
        abort(404)

    return zaobao_realtime.get_rss_xml_response(parameter=region, title_filter=title_filter)


@app.route(zhihu_router_path)
def zhihu_router():
    xml_response = zhihu_daily_router.get_rss_xml_response()
    return xml_response


router_refresh_job_scheduler(app)

if __name__ == '__main__':
    app.run()
