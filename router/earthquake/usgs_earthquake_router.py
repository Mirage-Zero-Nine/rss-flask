import logging

from flask import make_response

from data.feed_item_object import FeedItem
from data.rss_cache import feed_cache
from utils.cache_utilities import check_query
from utils.xml_utilities import generate_feed_object
from utils.get_link_content import load_json_response
from utils.router_constants import usgs_earthquake_link, usgs_earthquake_query_period
from utils.time_converter import convert_millisecond_to_datetime_with_format, convert_millisecond_to_datetime

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def generate_feed_rss():
    json_response = load_json_response(usgs_earthquake_link)
    feed_item_list = []
    for feature in json_response["features"]:
        loc = "<p>Location: " + feature["properties"]['place'] + '</p>'
        occurred_time = "<p>Time: " + \
                        str(convert_millisecond_to_datetime_with_format(feature["properties"]['time'], 7)) + \
                        '</p>'
        depth = '<p>Depth: ' + str(feature['geometry']['coordinates'][2]) + ' KM</p>'
        url = '<p>Details: <a href="%s">Click to see details...</a> ' % feature["properties"]['url']
        feed_item_object = FeedItem(
            title=feature["properties"]['title'],
            link=feature["properties"]['url'],
            author='USGS',
            created_time=convert_millisecond_to_datetime(feature["properties"]['time']),
            guid=feature["properties"]['ids'],
            description=loc + occurred_time + depth + url
        )
        feed_item_list.append(feed_item_object)

    feed = generate_feed_object(
        title="USGS - Earthquake Report",
        link="https://earthquake.usgs.gov/earthquakes/map",
        description="USGS Magnitude 2.5+ Earthquakes, Past Day",
        language='en-us',
        feed_item_list=feed_item_list
    )

    return feed


def get_rss_xml_response():
    usgs_key = "usgs/earthquake"

    bool_should_query = check_query(usgs_key, usgs_earthquake_query_period, "USGS")
    if bool_should_query is True:
        feed = generate_feed_rss()
        feed_cache[usgs_key] = feed
    else:
        feed = feed_cache[usgs_key]

    response_earthquake = make_response(feed.rss())
    response_earthquake.headers.set('Content-Type', 'application/rss+xml')

    return response_earthquake
