from flask import Flask
from router.twitter import twitter_router

app = Flask(__name__)


@app.route('/twitter/<user_name>')
def twitter_route(user_name):
    return twitter_router.generate_rss_xml(user_name)


@app.route('/')
def hello_world():
    return "Hello there."


if __name__ == '__main__':
    app.run()
