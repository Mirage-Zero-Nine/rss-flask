import datetime as dt

import pytz
from rfeed import Feed, Item, Guid


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


def generate_feed_object_for_new_router(title, link, description, language, last_build_time, feed_item_list):
    feed = Feed(
        title=title,
        link=link,
        description=description,
        language=language,
        lastBuildDate=last_build_time,
        items=create_item_list(feed_item_list)
    )

    return feed


def create_item_list(feed_item_list, is_perma_link=False):
    output_list = []
    for item in feed_item_list:
        generated_feed_item = Item(
            title=item.title,
            link=item.link,
            description=item.description,
            author=item.author,
            guid=Guid(item.guid, isPermaLink=is_perma_link),
            pubDate=item.created_time
        )

        output_list.append(generated_feed_item)
    return output_list
