zaobao_region_general_title = "联合早报 - 即时新闻"
zaobao_query_period = 10 * 60 * 1000  # 10 minutes
zaobao_time_convert_pattern = "%Y年%m月%d日 %I:%M %p"
zaobao_time_general_author = '联合早报'

zaobao_story_prefix = 'https://www.zaobao.com.sg'
zaobao_realtime_page_prefix = zaobao_story_prefix + "/realtime/"
zaobao_realtime_china_frontpage_prefix = zaobao_story_prefix + "/realtime/china"
zaobao_realtime_world_frontpage_prefix = zaobao_story_prefix + "/realtime/world"
zaobao_realtime_page_suffix = "?_wrapper_format=html&page="

zaobao_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Referer': 'https://www.zaobao.com.sg/realtime',
    'Host': 'www.zaobao.com.sg',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:97.0) Gecko/20100101 Firefox/97.0'
}

unwanted_div_class = [
    "settings-tray-editable",
    "article-meta",
    "field field-name-dynamic-twig-fieldnode-2020-font-size",

    "article-share-fb",
    "keywords",
    "newspost-holder",
    "cx_paywall_placeholder"
]
unwanted_div_id = [
    'innity-in-post',
    'NextPrevious',
    "dfp-ad-midarticlespecial",
    "outbrain-wrapper"
]

zaobao_region_world = "world"
zaobao_region_china = "china"

zaobao_region_parameter = {zaobao_region_world, zaobao_region_china}

feed_title_mapping = {
    zaobao_region_china: "联合早报 - 中港台即时新闻",
    zaobao_region_world: "联合早报 - 国际即时新闻"
}
feed_description_mapping = {
    zaobao_region_china: "中国的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。",
    zaobao_region_world: "国际的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。"
}
feed_prefix_mapping = {
    zaobao_region_china: zaobao_realtime_china_frontpage_prefix,
    zaobao_region_world: zaobao_realtime_world_frontpage_prefix
}

title_filter = '下午察'