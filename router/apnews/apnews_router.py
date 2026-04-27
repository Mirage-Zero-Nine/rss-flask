import logging

from router.base_router import BaseRouter
from utils.feed_item_object import FeedItem, Metadata, generate_cache_key, convert_router_path_to_cache_prefix
from utils.get_link_content import get_link_content_with_bs_no_params
from utils.router_constants import html_parser
from utils.time_converter import convert_millisecond_to_datetime


class ApnewsRouter(BaseRouter):
    """Router for AP News pages, supporting multiple topics via parameter."""

    TOPIC_URLS = {
        "top": "https://apnews.com/tag/apf-topnews",
        "business": "https://apnews.com/business",
    }

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        """Fetch the AP News page and extract article metadata.

        Args:
            parameter: dict with optional 'topic' key (e.g. {"topic": "business"}).
                       Defaults to "top" if not specified.
        """
        topic = (parameter or {}).get("topic", "top")
        url = self.TOPIC_URLS.get(topic, self.TOPIC_URLS["top"])
        logging.info("Router %s fetching AP News page for topic '%s' from %s", self.router_path, topic, url)

        soup = get_link_content_with_bs_no_params(url, html_parser)

        if soup is None:
            logging.error("Router %s failed to fetch AP News page for topic '%s' from %s", self.router_path, topic, url)
            return []
        cache_prefix = convert_router_path_to_cache_prefix(self.router_path)
        metadata_list = []

        # Article cards are <div class="PagePromo-content"> containing links to apnews.com/article/...
        promo_contents = soup.find_all("div", class_="PagePromo-content")
        logging.debug("Router %s found %d PagePromo-content elements", self.router_path, len(promo_contents))
        article_url_prefix = "https://apnews.com/article/"

        for i, promo in enumerate(promo_contents):
            # Find the article link
            link_tag = promo.find("a", href=True)
            if not link_tag:
                logging.debug("Router %s promo #%d: no anchor tag found", self.router_path, i)
                continue
            href = link_tag.get("href", "")
            if not href.startswith(article_url_prefix):
                logging.debug("Router %s promo #%d: link %s does not match article prefix", self.router_path, i, href)
                continue

            # Extract title from PagePromo-title > a > span.PagePromoContentIcons-text
            title_span = promo.find("span", class_="PagePromoContentIcons-text")
            title = title_span.get_text(strip=True) if title_span else link_tag.get_text(strip=True)
            if not title:
                logging.warning("Router %s promo #%d: empty title for link %s", self.router_path, i, href)

            # Extract description from PagePromo-description
            desc_div = promo.find("div", class_="PagePromo-description")
            description = ""
            if desc_div:
                desc_span = desc_div.find("span", class_="PagePromoContentIcons-text")
                description = desc_span.get_text(strip=True) if desc_span else ""

            # Extract timestamp from bsp-timestamp data-timestamp (milliseconds)
            created_time = None
            ts_div = promo.find("div", class_="PagePromo-date")
            if ts_div:
                ts_elem = ts_div.find("bsp-timestamp")
                if ts_elem and ts_elem.get("data-timestamp"):
                    try:
                        ms = int(ts_elem["data-timestamp"])
                        created_time = convert_millisecond_to_datetime(ms)
                    except (ValueError, TypeError):
                        logging.warning(
                            "Router %s promo #%d: invalid timestamp %s for link %s",
                            self.router_path, i, ts_elem.get("data-timestamp"), href,
                        )

            cache_key = generate_cache_key(cache_prefix, href)
            metadata = Metadata(
                title=title,
                link=href,
                author="The Associated Press",
                created_time=created_time,
                guid=href,
                cache_key=cache_key,
                flag=description,  # stashed description for _get_article_content
            )
            metadata_list.append(metadata)

        logging.info(
            "Router %s built %d article metadata entries from AP News topic '%s' (out of %d promo cards)",
            self.router_path, len(metadata_list), topic, len(promo_contents),
        )
        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        """Fetch full article body from the AP News story page.

        AP News article pages render body text inside <div class="RichTextStoryBody RichTextBody">
        containing <p> tags, possibly with nested <div> elements (ads, embeds).
        """
        logging.info("Router %s fetching article content link=%s", self.router_path, article_metadata.link)
        soup = get_link_content_with_bs_no_params(article_metadata.link, html_parser)

        if soup is None:
            logging.error("Router %s failed to fetch article page for %s", self.router_path, article_metadata.link)
            entry.description = article_metadata.flag or ""
            entry.persist_to_cache(self.router_path)
            return ""

        # Find the article body
        body_div = soup.find("div", class_="RichTextStoryBody")
        if body_div is None:
            body_div = soup.find("div", class_="RichTextBody")

        if body_div is None:
            logging.warning(
                "Router %s could not find RichTextStoryBody or RichTextBody for %s",
                self.router_path, article_metadata.link,
            )
            entry.description = article_metadata.flag or ""
            entry.persist_to_cache(self.router_path)
            return ""

        logging.debug("Router %s found article body for %s", self.router_path, article_metadata.link)

        # Extract text from <p> tags, stripping nested <div> elements (ads, embeds)
        paragraphs = body_div.find_all("p")
        logging.debug("Router %s found %d <p> tags in body for %s", self.router_path, len(paragraphs),
                      article_metadata.link)
        body_parts = []
        for p in paragraphs:
            # Remove nested divs (e.g., ads) but keep their text
            for div in p.find_all("div"):
                div.decompose()
            text = p.get_text(strip=True)
            if text:
                body_parts.append(f"<p>{text}</p>")

        # Extract images from the page.
        # Priority: first, try the main carousel in <main class="Page-main">
        # (the news-related photo). Fall back to filtered images in the body.
        img_tags = []

        # 1. Try to get the main carousel image from <main class="Page-main">
        #    (first slide that has an actual image, not a video slide)
        page_main = soup.find("main", class_="Page-main")
        if page_main:
            for slide in page_main.find_all("div", class_="Carousel-slide"):
                carousel_img = slide.find("img", class_="Image")
                if carousel_img:
                    src = carousel_img.get("data-flickity-lazyload") or carousel_img.get("src") or carousel_img.get(
                        "data-src")
                    alt = carousel_img.get("alt", "")
                    if src:
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = "https://apnews.com" + src
                        img_tags.append(f"<img src=\"{src}\" alt=\"{alt}\">")
                        logging.debug(
                            "Router %s extracted main carousel image from Page-main for %s",
                            self.router_path, article_metadata.link,
                        )
                    break

        # 2. Fallback: extract filtered images from the body if no carousel image found
        if not img_tags:
            images = body_div.find_all("img")
            logging.debug("Router %s found %d images in body for %s", self.router_path, len(images),
                          article_metadata.link)
            for img in images:
                # Skip decorative icons (e.g., comment button)
                img_classes = img.get("class", [])
                if "comment-icon" in img_classes:
                    continue

                # Skip author headshots (inside <picture data-crop="small-square">)
                parent = img.parent
                if parent and parent.name == "picture":
                    if parent.get("data-crop") == "small-square":
                        continue

                # Only keep carousel photos (identified by data-flickity-lazyload-srcset)
                lazy_src = img.get("data-flickity-lazyload")
                if not lazy_src:
                    continue

                src = lazy_src
                alt = img.get("alt", "")
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = "https://apnews.com" + src
                    img_tags.append(f"<img src=\"{src}\" alt=\"{alt}\">")

        if not body_parts:
            logging.warning(
                "Router %s extracted 0 non-empty paragraphs from body for %s; falling back to flag",
                self.router_path, article_metadata.link,
            )
            entry.description = article_metadata.flag or ""
        else:
            entry.description = "".join(body_parts)

        # Append images to description
        if img_tags:
            entry.description += "\n\n" + "\n".join(img_tags)

        # Populate remaining metadata
        entry.title = article_metadata.title
        entry.link = article_metadata.link
        entry.author = article_metadata.author
        entry.created_time = article_metadata.created_time
        entry.guid = article_metadata.guid

        entry.persist_to_cache(self.router_path)
        logging.info(
            "Router %s persisted article to cache link=%s (description length=%d)",
            self.router_path, article_metadata.link, len(entry.description),
        )
        return entry.description
