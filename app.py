from flask import Flask
from router.twitter import twitter_router
from router.zaobao import zaobao_router
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


@app.route('/zaobao/realtime/world')
def zaobao():
    xml_response = zaobao_router.get_rss_xml_response()
    return xml_response


@app.route('/')
def hello_world():
    return "Hello there."


if __name__ == '__main__':
    app.run()
