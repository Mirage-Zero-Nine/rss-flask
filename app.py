from flask import Flask
from router.twitter import twitter_router
from router.zaobao import zaobao_router

app = Flask(__name__)

@app.route('/twitter/<user_name>')
def twitter(user_name):
    return twitter_router.generate_rss_xml(user_name)


@app.route('/zaobao/realtime')
def zaobao():
    feed = zaobao_router.get_rss_xml()
    return feed


@app.route('/')
def hello_world():
    return "Hello there."


if __name__ == '__main__':
    app.run()
