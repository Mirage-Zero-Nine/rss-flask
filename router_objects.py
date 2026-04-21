from rss_flask.feed_registry import build_router_registry

router_registry = build_router_registry()

meta_tech_blog = router_registry["meta_tech_blog"]
cnbeta = router_registry["cnbeta"]
the_verge = router_registry["the_verge"]
usgs_earthquake_report = router_registry["usgs_earthquake_report"]
twitter_engineering_blog = router_registry["twitter_engineering_blog"]
zaobao_realtime = router_registry["zaobao_realtime"]
day_one_blog = router_registry["day_one_blog"]
nbc_news = router_registry["nbc_news"]
wsdot_news = router_registry["wsdot_news"]
zhihu_daily = router_registry["zhihu_daily"]
chinese_embassy_news = router_registry["chinese_embassy_news"]
jandan_news = router_registry["jandan_news"]
reuters_news = router_registry["reuters_news"]
sony_alpha_rumors = router_registry["sony_alpha_rumors"]
