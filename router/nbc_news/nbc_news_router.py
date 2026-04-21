from router.router_for_rss_feed import RouterForRssFeed
from utils.helpers import convert_time_with_pattern, decompose_div, decompose_tag_by_class_name
from utils.http_client import get_link_content_with_bs_no_params


class NbcNewsRouter(RouterForRssFeed):
    def _get_article_content(self, article_metadata, entry):
        soup = get_link_content_with_bs_no_params(entry.link).find("article", class_="styles_article__Ee5Ad article")

        if soup is not None:
            entry.created_time = convert_time_with_pattern(article_metadata.created_time, "%a, %d %b %Y %H:%M:%S %Z")
            byline_span = soup.find("span", class_="byline-name")
            entry.author = byline_span.text.strip() if byline_span else None

            div_tag = soup.find("div", class_="article-hero__media-container")
            if div_tag is not None:
                img_tag = div_tag.find("img")
                if img_tag is not None:
                    div_tag.replace_with(img_tag)

            decompose_div(soup, "ad-container")
            decompose_div(soup, "ad dn-print")
            decompose_div(soup, "taboolaReadMoreBelow")
            decompose_div(soup, "recommended-intersection-ref")
            decompose_div(soup, "article-social-share-top")
            decompose_div(soup, "expanded-byline-contributors articleBylineContainer")
            decompose_div(soup, "article-hero__video")
            decompose_tag_by_class_name(soup, "aside", "article-hero__unibrow-grid")

            entry.description = soup
            entry.save_to_cache(self.router_path)
        else:
            self._log_warning(
                "empty article content selector=article.styles_article__Ee5Ad.article "
                f"article_url={entry.link}"
            )
