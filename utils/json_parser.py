import json
import os
import datetime as dt

import pytz
from rfeed import Feed
from datetime import datetime

from utils.feed_item_object import FeedItem, convert_router_path_to_save_path_prefix, generate_json_name


def write_entry_to_json(output_file_path, feed_entries):
    feed_item_dicts = [item.__dict__ for item in feed_entries]
    json_file_path = output_file_path

    with open(json_file_path, 'w') as json_file:
        json.dump(feed_item_dicts, json_file, indent=4)

    print(f'Feed items saved to {json_file_path}')


def json_to_feed_entry(entry_path):
    with open(entry_path, 'r') as json_file:
        feed_entries_dic = json.load(json_file)

    feed_entries = []
    for entry_dic in feed_entries_dic:
        created_time = datetime.strptime(entry_dic['created_time'], '%Y-%m-%d %H:%M:%S')
        item = FeedItem(
            title=entry_dic['title'],
            link=entry_dic['link'],
            description=entry_dic['description'],
            author=entry_dic['author'],
            created_time=created_time,
            guid=entry_dic['guid'],
            with_content=entry_dic['with_content']
        )
        feed_entries.append(item)
    return feed_entries


def save_feed_to_json(feed, router_path, file_name):
    save_path_prefix = convert_router_path_to_save_path_prefix(router_path)

    # create a directory to save json
    os.makedirs(save_path_prefix, exist_ok=True)
    json_name = generate_json_name(save_path_prefix, file_name)

    with open(json_name, 'w') as json_file:
        json.dump({
            "title": feed.title,
            "link": feed.link,
            "description": feed.description,
            "language": feed.language,
            "lastBuildDate": feed.lastBuildDate.isoformat(),
            "items": feed.items,
        }, json_file)

    return feed


def read_feed_from_json(router_path, file_name):
    save_path_prefix = convert_router_path_to_save_path_prefix(router_path)
    json_name = generate_json_name(save_path_prefix, file_name)

    with open(json_name, 'r') as json_file:
        json_data = json.load(json_file)

    json_data['lastBuildDate'] = dt.datetime.fromisoformat(json_data['lastBuildDate']).astimezone(pytz.timezone('GMT'))

    return Feed(
        title=json_data.get("title"),
        link=json_data.get("link"),
        description=json_data.get("description"),
        language=json_data.get("language"),
        lastBuildDate=json_data['lastBuildDate'],
        items=json_data.get("items")
    )
