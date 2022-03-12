import datetime as dt
from rfeed import *


def create_item(title, link, description, author, guid, pubDate, isPermaLink):
    item = Item(
        title=title,
        link=link,
        description=description,
        author=author,
        guid=Guid(guid, isPermaLink=isPermaLink),
        pubDate=pubDate
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
