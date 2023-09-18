from data.feed_item_object import FeedItem
from router.router_for_json_feed import RouterForJsonFeed
from utils.router_constants import language_english
from utils.time_converter import convert_millisecond_to_datetime_with_format, convert_millisecond_to_datetime
from utils.xml_utilities import generate_feed_object


class UsgsEarthquakeRouter(RouterForJsonFeed):
    def _generate_feed_rss(self, link_filter=None, title_filter=None):
        json_response = self._load_json_response()
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
                author=self.name,  # they don't have a specific author
                created_time=convert_millisecond_to_datetime(feature["properties"]['time']),
                guid=feature["properties"]['ids'],
                description=loc + occurred_time + depth + url
            )
            feed_item_list.append(feed_item_object)

        feed = generate_feed_object(
            title=self.feed_title,
            link=self.original_link,
            description=self.description,
            language=language_english,
            feed_item_list=feed_item_list
        )

        return feed
