from flask import Flask
from router.twitter import twitter_router
from router.zaobao import zaobao_router
from router.dayone import dayone_router

app = Flask(__name__)


@app.route('/twitter/<user_name>')
def twitter(user_name):
    xml = twitter_router.generate_rss_xml(user_name)
    return xml


@app.route('/zaobao/realtime/world')
def zaobao():
    xml = zaobao_router.get_rss_xml()
    return xml


@app.route('/dayone')
def dayone():
    xml = dayone_router.get_day_one_xml()
    return xml


@app.route('/')
def hello_world():
    return "Hello there."


if __name__ == '__main__':
    app.run()
