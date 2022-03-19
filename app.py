from flask import Flask
from router.twitter import twitter_router
from router.zaobao import zaobao_realtime_router
from router.dayone import dayone_router
from router.jandan import jandan_router
from router.currency import currency_router

app = Flask(__name__)


@app.route('/currency/<currency_name>')
def currency(currency_name):
    xml_response = currency_router.get_rss_xml_response(currency_name)
    return xml_response


@app.route('/dayone')
def dayone():
    xml_response = dayone_router.get_rss_xml_response()
    return xml_response


@app.route('/jandan')
def jandan():
    return jandan_router.get_jandan_rss_xml_response()


@app.route('/twitter/<user_name>')
def twitter(user_name):
    xml_response = twitter_router.generate_rss_xml_response(user_name)
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


@app.route('/')
def hello_world():
    return "Hello there."


if __name__ == '__main__':
    app.run()
