import json
import logging
import os
import traceback
from datetime import datetime

from utils.feed_item_object import FeedItem, generate_json_name, convert_router_path_to_save_path_prefix


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


def read_feed_item_from_json(json_file_path):
    try:
        with open(json_file_path, 'r') as json_file:
            json_data = json.load(json_file)

            return FeedItem(
                title=json_data.get("title"),
                link=json_data.get("link"),
                description=json_data.get("description"),
                author=json_data.get("author"),
                guid=json_data.get("guid"),
                created_time=datetime.fromisoformat(json_data.get("created_time")) if json_data.get("created_time") else None,
                with_content=json_data.get("with_content")
            )

    except FileNotFoundError:
        logging.error(f"JSON file not found: {json_file_path}")
        logging.error(traceback.format_exc())  # Log error trace
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON file: {json_file_path}")
        logging.error(traceback.format_exc())  # Log error trace
        # Delete the JSON file if it cannot be loaded
        os.remove(json_file_path)
        logging.info(f"Deleted JSON file: {json_file_path}")

    return None
