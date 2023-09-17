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


def check_need_to_filter(link, title, link_filter, title_filter):
    if link_filter and link.startswith(link_filter):
        return True
    if title_filter and title.startswith(title_filter):
        return True

    return False
