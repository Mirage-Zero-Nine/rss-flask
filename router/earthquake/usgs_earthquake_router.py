import logging

from flask import make_response
from datetime import datetime

import constant.constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ
import data.feed_cache as fc

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def generate_feed_rss():
    json_response = glc.load_json_response(c.usgs_earthquake_link)
    feed_item_list = []
    for feature in json_response["features"]:
        loc = "<p>Location: " + feature["properties"]['place'] + '</p>'
        occurred_time = "<p>Time: " + \
                        str(tc.convert_millisecond_to_datetime_with_format(feature["properties"]['time'], 7)) + \
                        '</p>'
        depth = '<p>Depth: ' + str(feature['geometry']['coordinates'][2]) + ' KM</p>'
        url = '<p>Details: <a href="%s">Click to see details...</a> ' % feature["properties"]['url']
        feed_item_object = do.FeedItem(
            title=feature["properties"]['title'],
            link=feature["properties"]['url'],
            author='USGS',
            created_time=tc.convert_millisecond_to_datetime(feature["properties"]['time']),
            guid=feature["properties"]['ids'],
            description=loc + occurred_time + depth + url
        )
        feed_item_list.append(feed_item_object)

    feed = gxml.generate_rss_by_feed_object(
        title="USGS - Earthquake Report",
        link="https://earthquake.usgs.gov/earthquakes/map",
        description="USGS Magnitude 2.5+ Earthquakes, Past Day",
        language='en-us',
        feed_item_list=feed_item_list
    )

    return feed


def check_if_should_query(usgs_key):
    """
    Limit query to at most 1 time in 10 minutes.
    :return: if service should query now
    """

    # if it's the first query, or the last query happened more than 10 minutes, then query again
    if len(fc.feed_cache) == 0 or usgs_key not in fc.feed_cache.keys() or civ.check_should_query_no_state(
            datetime.timestamp(fc.feed_cache[usgs_key].lastBuildDate),
            c.usgs_earthquake_query_period
    ):
        return True

    return False


def get_rss_xml_response():
    usgs_key = "usgs/earthquake"

    bool_should_query = check_if_should_query(usgs_key)
    logging.info("Query USGS for this call: " + str(bool_should_query))
    if bool_should_query is True:
        feed = generate_feed_rss()
        fc.feed_cache[usgs_key] = feed
    else:
        feed = fc.feed_cache[usgs_key]

    response_earthquake = make_response(feed)
    response_earthquake.headers.set('Content-Type', 'application/rss+xml')

    return response_earthquake


if __name__ == '__main__':
    generate_feed_rss()
