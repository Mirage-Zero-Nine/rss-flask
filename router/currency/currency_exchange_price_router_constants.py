currency_exchange_price_name = "Currency Price Exchange "
currency_exchange_price_title = "中国银行外汇牌价 - 人民币兑美元"
currency_exchange_price_description = "中国银行人民币兑外币牌价"
currency_exchange_price_link = "http://www.boc.cn/sourcedb/whpj/"
currency_exchange_price_search_link = "https://srh.bankofchina.com/search/whpj/search_cn.jsp"
currency_exchange_price_query_period = 20 * 60 * 1000  # 20 minutes
currency_exchange_price_query_page_count = 10  # query 10 pages, only save the latest price in each hour
currency_exchange_price_time_convert_pattern = '%Y.%m.%d %H:%M:%S'
currency_exchange_price_cache_key = "currency/"
currency_exchange_price_parameter = {'usd'}
