import base64
import json
import logging
import os
from datetime import datetime

from utils.router_constants import data_path_prefix


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
        Remember to update attribute in save_to_json
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
        self.json_name = ""

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

    def save_to_json(self, router_path):
        """
        File name: /data/{router_path}/{encoded_link}.json
        Example: /data/meta-blog/{encoded_link}.json
        :param router_path: name of the router path
        """
        save_path_prefix = convert_router_path_to_save_path_prefix(router_path)

        # create a directory to save json
        os.makedirs(save_path_prefix, exist_ok=True)

        self.json_name = generate_json_name(save_path_prefix, self.guid)
        with open(self.json_name, 'w') as json_file:
            json.dump({
                "title": self.title,
                "link": self.link,
                "description": str(self.description),
                "author": self.author,
                "created_time": str(self.created_time),
                "guid": self.guid,
                "with_content": self.with_content
            }, json_file)


class Metadata:
    def __init__(self, title=None, link=None, author=None, guid=None, created_time=None, json_name=None, flag=None):
        """
        Remember to update attribute in save_to_json
        :param title: title of the entry
        :param link: link to the entry (also works as guid)
        :param author: author of the entry
        :param guid: guid of the entry (most likely should be the same as the link)
        :param created_time: create time for the entry
        :param json_name: json name of the entry
        :param flag: any mark required for later processing
        """
        self.title = title
        self.link = link
        self.author = author
        self.guid = guid
        self.created_time = created_time  # required to be a datatime object
        self.json_name = json_name
        self.flag =flag


def generate_json_name(prefix, name):
    json_name = base64.urlsafe_b64encode(name.encode('utf-8')).decode('utf-8').rstrip('=')
    if len(json_name) > 100:
        json_name = json_name[-100:]
    return f"{prefix}/{json_name}.json"


def convert_router_path_to_save_path_prefix(router_path):
    if router_path.startswith('/') is False:
        logging.error(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} Invalid path, it's not started with a '/': {router_path}")
        raise Exception("Invalid path, it's not started with a '/'")

    return f"{data_path_prefix}{router_path[1:].replace('/', '-')}"
