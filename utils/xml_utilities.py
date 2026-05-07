from rfeed import Feed, Item, Guid


def generate_feed_object_for_new_router(title, link, description, language, last_build_time, feed_item_list):
    items = [
        Item(
            title=item.title,
            link=item.link,
            description=item.description,
            author=item.author,
            guid=Guid(item.guid),
            pubDate=item.created_time
        )
        for item in feed_item_list
    ]
    return Feed(title=title, link=link, description=description, language=language, lastBuildDate=last_build_time, items=items)
