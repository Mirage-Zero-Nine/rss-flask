from utils.router_constants import zaobao_region_china, zaobao_region_world, zaobao_realtime_china_frontpage_prefix, \
    zaobao_realtime_world_frontpage_prefix

region_link_mapping = {
    zaobao_region_china: zaobao_realtime_china_frontpage_prefix,
    zaobao_region_world: zaobao_realtime_world_frontpage_prefix
}
feed_description_mapping = {
    zaobao_region_china: "中国的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。",
    zaobao_region_world: "国际的即时、评论、商业、体育、生活、科技与多媒体新闻，尽在联合早报。"
}
feed_title_mapping = {
    zaobao_region_china: "联合早报 - 中港台即时新闻",
    zaobao_region_world: "联合早报 - 国际即时新闻"
}
