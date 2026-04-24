import base64
import logging
from datetime import datetime

from utils.cache_store import write_feed_item_to_cache


class FeedItem:

    def __init__(self,
                 title=None,
                 link=None,
                 description=None,
                 author=None,
                 guid=None,
                 created_time=None,
                 with_content=False):
        """
        Remember to update attribute in persist_to_cache
        :param title: title of the entry
        :param link: link to the entry (also works as guid)
        :param description: content of the entry
        :param author: author of the entry
        :param guid: guid of the entry (most likely should be the same as the link)
        :param created_time: create time for the entry
        :param with_content: if current entry has the content (whether description is "" or not)
        """
        self.title = title
        self.link = link
        self.description = description  # main content in each feed
        self.author = author
        self.created_time = created_time  # required to be a datatime object
        self.guid = guid
        self.with_content = with_content  # if current item has query the source url and fill with content
        self.cache_key = ""

    def __repr__(self):
        # Handle None values by providing default values or converting to empty string
        title = self.title or ""
        link = self.link or ""
        author = self.author or ""
        created_time = str(self.created_time) if self.created_time else ""
        description = self.description or ""
        guid = self.guid or ""
        with_content = str(self.with_content)

        return "title: " + title + '\n' + \
            "link: " + link + '\n' + \
            "author: " + author + '\n' + \
            "created_time: " + created_time + '\n' + \
            "description: " + description + '\n' + \
            "guid: " + guid + '\n' + \
            "with content? " + with_content

    def persist_to_cache(self, router_path):
        """
        Store the feed item in Redis under the router-specific cache prefix.
        :param router_path: name of the router path
        """
        cache_prefix = convert_router_path_to_cache_prefix(router_path)
        identifier = self.guid or self.link or self.title or datetime.utcnow().isoformat()
        self.cache_key = generate_cache_key(cache_prefix, identifier)
        payload = {
            "title": self.title,
            "link": self.link,
            "description": str(self.description),
            "author": self.author,
            "created_time": str(self.created_time) if self.created_time else None,
            "guid": self.guid,
            "with_content": self.with_content
        }
        write_feed_item_to_cache(self.cache_key, payload)


class Metadata:
    def __init__(self, title=None, link=None, author=None, guid=None, created_time=None, cache_key=None, flag=None):
        """
        Remember to update attribute in persist_to_cache
        :param title: title of the entry
        :param link: link to the entry (also works as guid)
        :param author: author of the entry
        :param guid: guid of the entry (most likely should be the same as the link)
        :param created_time: create time for the entry
        :param cache_key: Redis key of the entry
        :param flag: any mark required for later processing
        """
        self.title = title
        self.link = link
        self.author = author
        self.guid = guid
        self.created_time = created_time  # required to be a datatime object
        self.cache_key = cache_key
        self.flag = flag


def generate_cache_key(prefix, name):
    encoded_name = base64.urlsafe_b64encode(name.encode('utf-8')).decode('utf-8').rstrip('=')
    if len(encoded_name) > 100:
        encoded_name = encoded_name[-100:]
    return f"{prefix}:{encoded_name}"


def convert_router_path_to_cache_prefix(router_path):
    if router_path.startswith('/') is False:
        logging.error(f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Invalid path, it's not started with a '/': {router_path}")
        raise Exception("Invalid path, it's not started with a '/'")

    sanitized = router_path[1:].replace('/', '-')
    return f"router_cache:{sanitized}"
