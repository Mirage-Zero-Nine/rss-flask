import datetime as dt
from datetime import datetime
from rfeed import *


def create_item(title, link, description, author, guid, created_time_string):
    item = Item(
        title=title,
        link=link,
        description=description,
        author=author,
        guid=Guid(guid),
        pubDate=datetime.strptime(created_time_string, '%Y-%m-%dT%H:%M:%S.%fZ')
    )

    return item


def generate_feed(title, link, description, language, items):
    feed = Feed(
        title=title,
        link=link,
        description=description,
        language=language,
        lastBuildDate=dt.datetime.now(),
        items=items
    )

    return feed.rss()
