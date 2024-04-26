reuters_fetch_api_base_link = 'https://www.reuters.com/pf/api/v3/content/fetch/'
reuters_site_link = "https://www.reuters.com/"
reuters_description = "'Reuters.com is your online source for the latest world news stories and current events, ensuring our readers up to date with any breaking news developments'"

# fetch a list of articles based on section
reuters_articles_list_api_link = 'articles-by-section-alias-or-id-v1?query='
# fetch individual article content
reuters_article_content_api_link = 'article-by-id-or-url-v1?query='

reuters_period = 10 * 60 * 1000  # 10 minutes

reuters_category = {
    "world",
    "business",
    "legal",
    "markets",
    "breakingviews",
    "technology",
    "graphics"
}

reuters_world_topic = {
    "africa",
    "americas",
    "asia-pacific",
    "china",
    "europe",
    "india",
    "middle-east",
    "uk",
    "us",
    "the-great-reboot",
    "reuters-next"
}

reuters_business_topic = {
    "aerospace-defense",
    "autos-transportation",
    "energy",
    "environment",
    "finance",
    "healthcare-pharmaceuticals",
    "media-telecom",
    "retail-consumer",
    "sustainable-business",
    "charged",
    "future-of-health",
    "future-of-money",
    "take-five",
    "reuters-impact"
}

reuters_legal_topic = {
    "government",
    "legalindustry",
    "litigation",
    "transactional"
}

reuters_category_with_topic = {
    "world": reuters_world_topic,
    "business": reuters_business_topic,
    "legal": reuters_legal_topic,
}

def is_valid_reuters_parameter(category: str, topic=None):
    if category not in reuters_category:
        return False

    if topic is not None:
        if category not in reuters_category_with_topic:
            return False
        topic_list = reuters_category_with_topic[category]
        if topic not in topic_list:
            return False

    return True
