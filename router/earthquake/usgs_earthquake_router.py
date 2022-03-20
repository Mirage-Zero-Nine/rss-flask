import time
import logging

from flask import make_response

import constant.constants as c
import utils.get_link_content as glc
import data.feed_item_object as do
import utils.generate_xml as gxml
import utils.time_converter as tc
import utils.check_if_valid as civ

started_time_earthquake = round(time.time() * 1000)
should_query_earthquake = None
response_earthquake = None

logging.basicConfig(filename='./log/application.log', encoding='utf-8', level=logging.DEBUG)


def generate_feed_rss():
    json_response = glc.load_json_response(c.usgs_earthquake_link)
    feed_item_list = []
    for feature in json_response["features"]:
        loc = "<p>Location: " + feature["properties"]['place'] + '</p>'
        occurred_time = "<p>Time: " + \
                        tc.convert_millisecond_to_datetime(feature["properties"]['time']).isoformat() + \
                        '</p>'
        depth = '<p>Depth: ' + str(feature['geometry']['coordinates'][2]) + ' KM</p>'
        url = '<p>URL: ' + feature["properties"]['url'] + '</p>'

        feed_item_object = do.FeedItem(
            title=feature["properties"]['title'],
            link=feature["properties"]['url'],
            author='USGS',
            created_time=tc.convert_millisecond_to_datetime(feature["properties"]['time']),
            guid=feature["properties"]['ids'],
            description=loc + occurred_time + url + depth
        )
        feed_item_list.append(feed_item_object)
        # print(feature["properties"]['title'])
        # print(feature["properties"]['place'])
        # print(feature["properties"]['mag'])
        # print(feature['geometry']['coordinates'][2])

    feed = gxml.generate_rss_by_feed_object(
        title="USGS - Earthquake Report",
        link="https://earthquake.usgs.gov/earthquakes/map",
        description="USGS Magnitude 2.5+ Earthquakes, Past Day",
        language='en-us',
        feed_item_list=feed_item_list
    )

    return feed


def check_if_should_query():
    """
    Limit query to at most 1 time in 10 minutes.
    :return: if service should query now
    """
    global should_query_earthquake
    global started_time_earthquake

    # if it's the first query, or the last query happened more than 10 minutes, then query again
    if civ.check_should_query(should_query_earthquake, started_time_earthquake, c.usgs_earthquake_query_period):
        should_query_earthquake = False
        started_time_earthquake = round(time.time() * 1000)
        return True

    return False


def get_rss_xml_response():
    global response_earthquake

    bool_should_query = check_if_should_query()
    logging.info(
        "Query for this call: " +
        str(bool_should_query) +
        ", current start time: " +
        str(started_time_earthquake)
    )
    if bool_should_query is True:
        feed = generate_feed_rss()
        response_earthquake = make_response(feed)
        response_earthquake.headers.set('Content-Type', 'application/rss+xml')

    return response_earthquake


if __name__ == '__main__':
    generate_feed_rss()
