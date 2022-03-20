# router query period
jandan_query_period = 2 * 60 * 60 * 1000  # 2 hours
dayone_query_period = 6 * 60 * 60 * 1000  # 6 hours
twitter_query_period = 10 * 60 * 1000  # 10 minutes
zaobao_query_period = 15 * 60 * 1000  # 15 minutes
currency_query_period = 10 * 60 * 1000  # 10 minutes
reuters_query_period = 10 * 60 * 1000  # 10 minutes
usgs_earthquake_query_period = 10 * 60 * 1000  # 10 minutes

currency_query_page_count = 5  # query 6 pages for currency exchange price list

currency_time_convert_pattern = '%Y.%m.%d %H:%M:%S'
zaobao_time_convert_pattern = "%Y年%m月%d日 %I:%M %p"
dayone_time_convert_pattern = '%B %d, %Y'
jandan_time_convert_pattern = "%Y.%m.%d , %H:%M"

html_parser = 'html.parser'

get_user_id_by_user_name = 'getUserIdByName'
get_tweet_by_user_id = 'getTweetByUserId'
get_tweet_by_tweet_id = 'getTweetByTweetId'

tweet_field = "tweet.fields"
expansions = "expansions"
media_fields = "media.fields"
place_fields = "place.fields"

data = "data"
created_at = "created_at"
tweet_id = "id"

twitter_token = "twitter_token"
token = "token"
pagination_token = "pagination_token"
meta = "meta"
next_token = "next_token"

tweet_link_prefix = "https://twitter.com/SeattlePD/status/"
twitter_prefix = "https://twitter.com/"

zaobao_realtime_world_frontpage_prefix = "https://www.zaobao.com.sg/realtime/world"
zaobao_realtime_china_frontpage_prefix = "https://www.zaobao.com.sg/realtime/china"
zaobao_story_prefix = 'https://www.zaobao.com.sg'
zaobao_realtime_world_page_prefix = 'https://www.zaobao.com.sg/realtime/world?_wrapper_format=html&page='
zaobao_realtime_page_prefix = "https://www.zaobao.com.sg/realtime/"
zaobao_realtime_page_suffix = "?_wrapper_format=html&page="
zaobao_region_world = "world"
zaobao_region_china = "china"

zaobao_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Referer': 'https://www.zaobao.com.sg/realtime',
    'Host': 'www.zaobao.com.sg',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0'
}

dayone_blog_link = "https://dayoneapp.com/blog/"

jandan_page_prefix = "http://jandan.net/"

currency_search_link = "https://srh.bankofchina.com/search/whpj/search_cn.jsp"
currency_link = "http://www.boc.cn/sourcedb/whpj/"
currency_usd_payload_data = {
    "erectDate": "",
    "nothing": "",
    "pjname": "美元",
    "head": "head_620.js",
    "bottom": "bottom_591.js"
}

reuters_page_link = "https://cn.reuters.com/assets/jsonWireNews?limit=20"
reuters_article_link_prefix = "https://cn.reuters.com"
reuters_source_link = "https://cn.reuters.com/theWire"  # can not directly get contents from this link
reuters_static_source_prefix = "https://static.reuters.com/resources/r/"
reuters_header = {
    "Host": "cn.reuters.com",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0",
    "Accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1"
}

usgs_earthquake_link = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
