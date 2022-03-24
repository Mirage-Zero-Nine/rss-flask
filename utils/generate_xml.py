import datetime as dt

import pytz
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


def create_item_list(feed_item_list):
    output_list = []
    for item in feed_item_list:
        generated_feed_item = create_item(
            title=item.title,
            link=item.link,
            description=item.description,
            author=item.author,
            guid=item.guid,
            pubDate=item.created_time,
            isPermaLink=False
        )
        output_list.append(generated_feed_item)
    return output_list


def generate_feed_object(title, link, description, language, feed_item_list):
    feed = Feed(
        title=title,
        link=link,
        description=description,
        language=language,
        lastBuildDate=dt.datetime.now(pytz.timezone('GMT')),
        items=create_item_list(feed_item_list)
    )

    return feed


if __name__ == '__main__':
    print(dt.datetime.now(pytz.timezone('GMT')))
