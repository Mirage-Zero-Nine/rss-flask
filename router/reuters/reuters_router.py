import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from html import unescape
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from router.base_router import BaseRouter
from router.reuters.reuters_constants import (
    reuters_articles_list_api_link,
    reuters_article_content_api_link,
    reuters_site_link,
    reuters_description,
    headers,
)
from utils.cache_store import (
    acquire_cache_lock,
    read_feed_item_from_cache,
    read_last_build_time,
    read_metadata_list,
    release_cache_lock,
    replace_metadata_list,
    write_last_build_time,
)
from utils.feed_item_object import Metadata, generate_cache_key, convert_router_path_to_cache_prefix, FeedItem
from utils.log_context import log_external_fetch, reset_current_router, set_current_router
from utils.router_constants import html_parser, language_english
from utils.time_converter import convert_time_with_pattern
from utils.xml_utilities import generate_feed_object_for_new_router


class ReutersRouter(BaseRouter):
    """Reuters router."""

    default_article_list_size = 20
    combined_categories = {"world", "business"}
    yahoo_reuters_page = "https://profiles.yahoo.com/brands/reuters/"
    _title_match_threshold = timedelta(hours=3)
    _cache_lock_retry_seconds = 1.5
    _REQUEST_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.4 Safari/605.1.15",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join(title.strip().split())

    @staticmethod
    def _parse_to_utc_datetime(value) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError:
                return None
        else:
            return None

        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def _build_router_cache_key(self, parameter=None) -> str:
        if parameter is None:
            return self.router_path
        values = [str(value) for value in parameter.values()]
        return f"{self.router_path}/{'/'.join(values)}"

    def _combined_parameter(self, parameter) -> bool:
        return (
            isinstance(parameter, dict)
            and parameter.get("category") in self.combined_categories
        )

    def _metadata_list_cache_key(self, parameter=None) -> str:
        return self._build_article_list_cache_key(self._build_router_cache_key(parameter))

    def _lock_name_for_category(self, category: str) -> str:
        return f"reuters-combined-metadata:{category}"

    def _acquire_metadata_lock(self, category: str, source: str, incoming_count: int) -> str | None:
        lock_name = self._lock_name_for_category(category)
        token = acquire_cache_lock(lock_name)
        if token is not None:
            return token

        time.sleep(self._cache_lock_retry_seconds)
        token = acquire_cache_lock(lock_name)
        if token is None:
            logging.warning(
                "Reuters combined metadata lock unavailable; skipping metadata write lock=%s category=%s source=%s incoming_count=%d",
                lock_name,
                category,
                source,
                incoming_count,
            )
        return token

    def _release_metadata_lock(self, category: str, token: str) -> None:
        release_cache_lock(self._lock_name_for_category(category), token)

    def _resolve_title_cache_key_collision(
        self,
        candidate_cache_key: str,
        key_name: str,
        created_time: datetime | None,
        stable_source_identifier: str,
        existing_metadata: list[dict] | None,
    ) -> str:
        for item in existing_metadata or []:
            if item.get("cache_key") != candidate_cache_key:
                continue
            item_time = self._parse_to_utc_datetime(item.get("created_time"))
            if created_time and item_time and abs(created_time - item_time) <= self._title_match_threshold:
                return candidate_cache_key

            return generate_cache_key(
                convert_router_path_to_cache_prefix(self.router_path),
                f"{key_name}|{stable_source_identifier}",
            )
        return candidate_cache_key

    def _build_title_cache_key(
        self,
        title: str,
        created_time,
        stable_source_identifier: str,
        existing_metadata: list[dict] | None,
    ) -> str:
        normalized = self._normalize_title(title)
        comparable = normalized.casefold()
        parsed_time = self._parse_to_utc_datetime(created_time)

        for item in existing_metadata or []:
            item_normalized = self._normalize_title(str(item.get("title", "")))
            if item_normalized.casefold() != comparable:
                continue

            item_time = self._parse_to_utc_datetime(item.get("created_time"))
            if parsed_time and item_time and abs(parsed_time - item_time) <= self._title_match_threshold:
                cache_key = item.get("cache_key")
                if isinstance(cache_key, str) and cache_key:
                    return cache_key

        if parsed_time:
            key_name = f"{normalized}|{parsed_time:%Y-%m-%d}"
        else:
            logging.warning("Unable to parse created_time for title-based Reuters cache key title=%s", title)
            key_name = normalized

        candidate_cache_key = generate_cache_key(
            convert_router_path_to_cache_prefix(self.router_path),
            key_name,
        )
        return self._resolve_title_cache_key_collision(
            candidate_cache_key=candidate_cache_key,
            key_name=key_name,
            created_time=parsed_time,
            stable_source_identifier=stable_source_identifier,
            existing_metadata=existing_metadata,
        )

    @staticmethod
    def _dict_to_metadata(metadata_dict: dict) -> Metadata:
        payload = dict(metadata_dict)
        if "json_name" in payload and "cache_key" not in payload:
            payload["cache_key"] = payload.pop("json_name")
        return Metadata(**payload)

    def _merge_reuters_metadata(
        self,
        existing_metadata: list[dict],
        incoming_reuters_metadata: list[Metadata],
    ) -> list[Metadata]:
        incoming_keys = {metadata.cache_key for metadata in incoming_reuters_metadata}
        merged = list(incoming_reuters_metadata)
        for metadata_dict in existing_metadata:
            if metadata_dict.get("cache_key") in incoming_keys:
                continue
            merged.append(self._dict_to_metadata(metadata_dict))
        return merged

    def _merge_yahoo_metadata(
        self,
        existing_metadata: list[dict],
        incoming_yahoo_metadata: list[Metadata],
    ) -> list[Metadata]:
        existing_keys = {item.get("cache_key") for item in existing_metadata}
        merged = [metadata for metadata in incoming_yahoo_metadata if metadata.cache_key not in existing_keys]
        for metadata_dict in existing_metadata:
            merged.append(self._dict_to_metadata(metadata_dict))
        return merged

    @staticmethod
    def _fetch_with_requests(url: str, timeout: int = 30) -> dict:
        """Fetch URL via plain requests and return structured result."""
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            status = response.status_code
            try:
                json_data = response.json()
            except ValueError:
                json_data = None
            return {
                'status': status,
                'json': json_data,
                'error': None,
                'url': response.url,
                'text': response.text,
            }
        except requests.RequestException as e:
            logging.warning("Request error for %s: %s", url, e)
            return {
                'status': None,
                'json': None,
                'error': str(e),
                'url': url,
                'text': '',
            }

    @staticmethod
    def __resolve_created_time(article):
        published_time = article.get("published_time")
        if published_time:
            try:
                return convert_time_with_pattern(published_time, "%Y-%m-%dT%H:%M:%S.%fZ").isoformat()
            except ValueError:
                try:
                    return convert_time_with_pattern(published_time, "%Y-%m-%dT%H:%M:%SZ").isoformat()
                except ValueError:
                    pass

        logging.warning(
            "Reuters article id=%s title=%s link=%s has missing or invalid published_time=%s; created_time unavailable",
            article.get("id", "<unknown>"),
            article.get("title", "<missing>"),
            article.get("canonical_url", "<missing>"),
            published_time,
        )
        return None

    @staticmethod
    def __is_captcha_challenge(data):
        return isinstance(data, dict) and "url" in data and "captcha" in str(data.get("url", "")).lower()

    @staticmethod
    def __is_bot_challenge_text(text: str | None) -> bool:
        if not text:
            return False

        normalized = text.lower()
        return (
            "enable javascript" in normalized
            or "please enable js" in normalized
            or "disable any ad blocker" in normalized
            or "captcha" in normalized
        )

    @staticmethod
    def __extract_reuters_result(data, context, response, json_query, resource_link=None) -> dict | None:
        if not isinstance(data, dict):
            logging.error(
                "Unexpected Reuters %s payload type. resource_link=%s status=%s url=%s query=%s payload_type=%s",
                context,
                resource_link,
                response.get('status'),
                response.get('url'),
                json_query,
                type(data).__name__,
            )
            return None

        if ReutersRouter.__is_captcha_challenge(data):
            logging.error(
                "Reuters %s blocked by captcha. resource_link=%s status=%s challenge_url=%s",
                context,
                resource_link,
                response.get('status'),
                data.get("url"),
            )
            return None

        result = data.get("result")
        if isinstance(result, dict):
            return result

        logging.error(
            "Reuters %s payload missing result object. resource_link=%s status=%s url=%s query=%s top_level_keys=%s payload_snippet=%s",
            context,
            resource_link,
            response.get('status'),
            response.get('url'),
            json_query,
            sorted(data.keys()),
            (response.get('text') or '').replace('\n', ' ')[:200],
        )
        return None

    @staticmethod
    def __build_api_request_link(root_url, json_query):
        return root_url + quote(json_query, safe="")

    def _get_articles_list(self, parameter=None, link_filter=None, title_filter=None):
        metadata_list = []
        category = parameter['category']
        existing_metadata = self._read_cached_metadata_dicts(parameter=parameter)

        logging.info("Reuters list request category=%s size=%s", category, self.default_article_list_size)
        section_id = f"/{category}/"
        root_url = self.articles_link + reuters_articles_list_api_link

        json_query = json.dumps({
            'offset': 0,
            'size': self.default_article_list_size,
            'section_id': section_id,
            'website': 'reuters',
        })
        request_link = self.__build_api_request_link(root_url, json_query)

        log_external_fetch(
            "requests",
            request_link,
            resource="reuters_articles_list",
        )
        response_data = self._fetch_with_requests(request_link)

        if response_data.get('error'):
            logging.error(
                "Request error fetching Reuters articles list category=%s request_link=%s: %s",
                category,
                request_link,
                response_data['error'],
            )
            return []

        if response_data.get('status') != 200:
            logging.error(
                "Reuters API returned status=%s for articles list category=%s request_link=%s response_url=%s",
                response_data.get('status'),
                category,
                request_link,
                response_data.get('url'),
            )
            return []

        data = response_data.get('json')
        if not data:
            logging.error(
                "Reuters articles list response is empty category=%s request_link=%s response_url=%s snippet=%s",
                category,
                request_link,
                response_data.get('url'),
                (response_data.get('text') or '').replace('\n', ' ')[:200],
            )
            return []

        result = self.__extract_reuters_result(
            data=data,
            context="articles list",
            response=response_data,
            json_query=json_query,
            resource_link=request_link,
        )
        if result is None:
            logging.error(
                "Reuters articles list extract failed category=%s request_link=%s",
                category,
                request_link,
            )
            return []

        articles = result.get("articles", [])
        for article in articles:
            if not article.get("title"):
                continue
            if not article.get("canonical_url"):
                continue
            if link_filter and link_filter not in article.get("canonical_url", ""):
                continue
            if title_filter and title_filter in article.get("title", ""):
                continue
            canonical_url = article.get("canonical_url")
            full_link = "https://www.reuters.com" + canonical_url
            created_time = self.__resolve_created_time(article)
            cache_key = self._build_title_cache_key(
                title=article.get('title', ''),
                created_time=created_time,
                stable_source_identifier=article.get("id", "") or full_link,
                existing_metadata=existing_metadata,
            )

            metadata_list.append(Metadata(
                title=article.get('title', ''),
                link=full_link,
                guid=article.get("id", ""),
                created_time=created_time,
                cache_key=cache_key,
            ))

        logging.info("Reuters built %d metadata entries for category=%s", len(metadata_list), category)
        return metadata_list

    def _get_article_content(self, article_metadata: Metadata, entry: FeedItem):
        if self._get_reuters_article_content(article_metadata, entry):
            entry.persist_to_cache(self.router_path, cache_key_override=article_metadata.cache_key)

    def _get_reuters_article_content(self, article_metadata: Metadata, entry: FeedItem) -> bool:
        article_id = article_metadata.guid
        root_url = self.articles_link + reuters_article_content_api_link
        json_query = json.dumps({
            'id': article_id,
            'website': 'reuters',
        })
        request_link = self.__build_api_request_link(root_url, json_query)

        log_external_fetch(
            "requests",
            request_link,
            resource="reuters_article_content",
            article_link=article_metadata.link,
        )
        response_data = self._fetch_with_requests(request_link)

        if response_data.get('error'):
            logging.error(
                "Request error fetching Reuters article content article_id=%s link=%s request_link=%s: %s",
                article_id,
                article_metadata.link,
                request_link,
                response_data['error'],
            )
            return False

        if response_data.get('status') != 200:
            logging.error(
                "Reuters API returned status=%s for article_id=%s link=%s request_link=%s response_url=%s",
                response_data.get('status'),
                article_id,
                article_metadata.link,
                request_link,
                response_data.get('url'),
            )
            if self.__is_bot_challenge_text(response_data.get('text')):
                logging.warning(
                    "Reuters API content response looks like bot-challenge content for article_id=%s link=%s",
                    article_id,
                    article_metadata.link,
                )
            return False

        data = response_data.get('json')
        if not data:
            logging.error(
                "Reuters article content response is empty for article_id=%s link=%s request_link=%s response_url=%s snippet=%s",
                article_id,
                article_metadata.link,
                request_link,
                response_data.get('url'),
                (response_data.get('text') or '').replace('\n', ' ')[:200],
            )
            if self.__is_bot_challenge_text(response_data.get('text')):
                logging.warning(
                    "Reuters API content response looks like bot-challenge content for article_id=%s link=%s",
                    article_id,
                    article_metadata.link,
                )
            return False

        result = self.__extract_reuters_result(
            data=data,
            context=f"article content {article_id}",
            response=response_data,
            json_query=json_query,
            resource_link=request_link,
        )
        if result is None:
            return False

        entry.description = ''
        entry.guid = article_metadata.guid
        entry.created_time = self._parse_to_utc_datetime(article_metadata.created_time) or article_metadata.created_time

        if "related_content" in result:
            related_content = result["related_content"]
            if "images" in related_content:
                for image in related_content["images"]:
                    if "url" in image:
                        entry.description += "<figure>"
                        entry.description += f"<img src=\"{image['url']}\" alt=\"Image\">"
                        if "caption" in image:
                            entry.description += f"<figcaption>{image['caption']}</figcaption>"
                        entry.description += "</figure>"
            elif "galleries" in related_content:
                for gallery in related_content.get("galleries", []):
                    for element in gallery.get("content_elements", []):
                        if element.get("type") == "image" and "url" in element:
                            entry.description += "<figure>"
                            entry.description += f"<img src=\"{element['url']}\" alt=\"Image\">"
                            if "caption" in element:
                                entry.description += f"<figcaption>{element['caption']}</figcaption>"
                            entry.description += "</figure>"

        content = result.get('content_elements')
        if not isinstance(content, list):
            logging.warning(
                "Reuters article content payload missing content_elements list for %s link=%s request_link=%s response_url=%s",
                article_metadata.guid,
                article_metadata.link,
                request_link,
                response_data.get('url'),
            )
            return False

        for p in content:
            if isinstance(p, dict) and p.get("type") == "paragraph" and p.get("content"):
                entry.description += "<p>" + p["content"] + "</p>"

        if not entry.description:
            logging.warning(
                "Reuters built empty description for article id=%s link=%s",
                article_id, article_metadata.link,
            )
            return False

        if self.__is_bot_challenge_text(entry.description):
            logging.warning(
                "Reuters API built bot-challenge-like content for article id=%s link=%s; skipping cache write",
                article_id,
                article_metadata.link,
            )
            entry.description = None
            return False

        return True

    def _build_reuters_article_entry(self, article_metadata: Metadata) -> FeedItem | None:
        entry = FeedItem(
            title=article_metadata.title,
            link=article_metadata.link,
            guid=article_metadata.guid,
            author=article_metadata.author,
            created_time=article_metadata.created_time,
        )
        token = set_current_router(self.router_path)
        try:
            if self._get_reuters_article_content(article_metadata, entry):
                return entry
            logging.warning("Reuters content unavailable for %s", article_metadata.link)
        except Exception:
            logging.exception("Reuters content fetch failed for %s", article_metadata.link)
        finally:
            reset_current_router(token)
        return None

    def refresh_cache(
        self,
        parameter=None,
        link_filter=None,
        title_filter=None,
        force: bool = False,
    ) -> bool:
        if not self._combined_parameter(parameter):
            return super().refresh_cache(
                parameter=parameter,
                link_filter=link_filter,
                title_filter=title_filter,
                force=force,
            )

        category = parameter["category"]
        router_cache_key = self._build_router_cache_key(parameter)
        article_list_key = self._metadata_list_cache_key(parameter)
        cached_metadata = read_metadata_list(article_list_key)
        last_build_time = read_last_build_time(router_cache_key)
        if (
            force is False
            and last_build_time
            and cached_metadata
            and round(datetime.now().timestamp() * 1000) - round(last_build_time.timestamp() * 1000) <= int(self.period)
        ):
            logging.info("Reuters combined cache still fresh for category=%s, skipping refresh", category)
            return False

        try:
            incoming_metadata = self._get_articles_list(
                parameter=parameter,
                link_filter=link_filter,
                title_filter=title_filter,
            )
        except Exception:
            logging.exception("Reuters combined article list fetch failed for category=%s", category)
            return False

        if not incoming_metadata:
            logging.warning("Reuters combined refresh returned 0 articles for category=%s; keeping existing metadata", category)
            return False

        fetched_entries: dict[str, FeedItem] = {}
        for metadata in incoming_metadata:
            entry = self._build_reuters_article_entry(metadata)
            if entry and entry.description:
                fetched_entries[metadata.cache_key] = entry

        token = self._acquire_metadata_lock(category, "reuters", len(incoming_metadata))
        if token is None:
            return False

        try:
            latest_metadata = read_metadata_list(article_list_key) or []
            final_metadata: list[Metadata] = []
            for metadata in incoming_metadata:
                provisional_key = metadata.cache_key
                metadata.cache_key = self._build_title_cache_key(
                    title=metadata.title,
                    created_time=metadata.created_time,
                    stable_source_identifier=metadata.guid or metadata.link,
                    existing_metadata=latest_metadata,
                )
                entry = fetched_entries.get(provisional_key)
                if entry and entry.description:
                    entry.persist_to_cache(self.router_path, cache_key_override=metadata.cache_key)
                final_metadata.append(metadata)

            merged_metadata = self._merge_reuters_metadata(latest_metadata, final_metadata)
            replace_metadata_list(article_list_key, merged_metadata)
            last_build_time = datetime.now(timezone.utc)
            write_last_build_time(router_cache_key, last_build_time)
            logging.info(
                "Reuters combined refresh published %d metadata items for category=%s fetched_entries=%d",
                len(final_metadata),
                category,
                len(fetched_entries),
            )
            return True
        finally:
            self._release_metadata_lock(category, token)

    def _fetch_yahoo_page(self, url):
        logging.info("Reuters Yahoo-source fetching URL=%s", url)
        try:
            response = requests.get(url, headers=self._REQUEST_HEADERS, timeout=15)
            logging.debug("Reuters Yahoo-source fetch status=%d length=%d", response.status_code, len(response.text))
            return BeautifulSoup(response.text, html_parser)
        except Exception:
            logging.exception("Reuters Yahoo-source failed to fetch %s", url)
            return None

    def _parse_yahoo_pub_dates(self, soup) -> dict[str, str]:
        pub_dates: dict[str, str] = {}
        ld_script = soup.find("script", type="application/ld+json")
        if not ld_script:
            return pub_dates

        try:
            ld_data = json.loads(ld_script.string)
        except (json.JSONDecodeError, TypeError):
            logging.warning("Reuters Yahoo-source failed to parse JSON-LD timestamps")
            return pub_dates

        if isinstance(ld_data, dict):
            for part in ld_data.get("hasPart", []):
                if not isinstance(part, dict):
                    continue
                url = part.get("url", "")
                date = part.get("datePublished") or part.get("uploadDate")
                if url and date:
                    pub_dates[url] = date
        return pub_dates

    def _parse_yahoo_articles(self, soup, category: str, existing_metadata: list[dict] | None) -> list[Metadata]:
        pub_dates = self._parse_yahoo_pub_dates(soup)
        strm = soup.find("div", id="strm")
        if not strm:
            logging.warning("Reuters Yahoo-source could not find #strm section")
            return []

        links = strm.find_all("a", attrs={"data-ylk": lambda value: value and "elm:hdln" in value and "subsec:publisher-brand" in value})
        metadata_list: list[Metadata] = []
        seen_titles: set[str] = set()
        for link in links:
            ylk = link.get("data-ylk", "")
            cat_match = re.search(r"cnt_tpc:([^;]+)", ylk)
            if not cat_match or cat_match.group(1).lower() != category:
                continue

            href = link.get("href", "")
            title = self._normalize_title(link.get_text(strip=True))
            if not href or not title:
                continue
            if title.casefold() in seen_titles:
                continue
            seen_titles.add(title.casefold())
            created_time = pub_dates.get(href)
            cache_key = self._build_title_cache_key(
                title=title,
                created_time=created_time,
                stable_source_identifier=href,
                existing_metadata=existing_metadata,
            )
            metadata_list.append(Metadata(
                title=title,
                link=href,
                author="Reuters",
                created_time=created_time,
                guid=href,
                cache_key=cache_key,
            ))

        logging.info("Reuters Yahoo-source parsed %d %s articles", len(metadata_list), category)
        return metadata_list

    def _remove_trading_disclosure_tags(self, article_tag) -> int:
        removed_count = 0
        while True:
            disclosure_text = article_tag.find(string=lambda text: text and text.strip() == "Trading disclosure")
            if not disclosure_text:
                return removed_count

            disclosure_tag = disclosure_text.find_parent("section", class_=lambda c: c and "ticker-list" in c)
            if not disclosure_tag:
                disclosure_tag = disclosure_text.find_parent("footer")
            if not disclosure_tag:
                disclosure_tag = disclosure_text.parent

            disclosure_tag.decompose()
            removed_count += 1

    def _iter_json_ld_objects(self, soup):
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except (json.JSONDecodeError, TypeError):
                continue

            if isinstance(data, dict):
                if isinstance(data.get("@graph"), list):
                    for item in data["@graph"]:
                        if isinstance(item, dict):
                            yield item
                else:
                    yield data
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        yield item

    @staticmethod
    def _extract_json_ld_image_url(ld) -> str:
        thumbnail = ld.get("thumbnailUrl")
        if isinstance(thumbnail, list):
            thumbnail = next((url for url in thumbnail if isinstance(url, str)), "")
        if isinstance(thumbnail, str) and thumbnail:
            return thumbnail

        image = ld.get("image")
        if isinstance(image, str):
            return image
        if isinstance(image, dict):
            url = image.get("url")
            return url if isinstance(url, str) else ""
        if isinstance(image, list):
            for item in image:
                if isinstance(item, str):
                    return item
                if isinstance(item, dict) and isinstance(item.get("url"), str):
                    return item["url"]
        return ""

    def _get_yahoo_article_content(self, article_metadata: Metadata, entry: FeedItem) -> None:
        logging.info("Reuters Yahoo-source fetching article title='%s' link=%s", article_metadata.title[:50], article_metadata.link)
        try:
            response = requests.get(article_metadata.link, headers=self._REQUEST_HEADERS, timeout=15)
            soup = BeautifulSoup(response.text, html_parser)
        except Exception:
            logging.exception("Reuters Yahoo-source failed to fetch article page for %s", article_metadata.link)
            entry.description = ""
            return

        time_tag = soup.find("time")
        time_text = ""
        if time_tag:
            time_text = time_tag.get_text(strip=True)
            if time_tag.get("datetime"):
                entry.created_time = time_tag["datetime"]

        author_span = soup.find("span", class_=lambda c: c and "byline-attr-author" in c)
        if author_span:
            entry.author = author_span.get_text(strip=True)

        parts = []
        content_found = False
        if time_text:
            parts.append(f"<p>{time_text}</p>")

        article_tag = soup.find("article")
        if article_tag:
            self._remove_trading_disclosure_tags(article_tag)
            for fig in article_tag.find_all("figure"):
                img = fig.find("img")
                caption = fig.find("figcaption")
                if img and img.get("src"):
                    parts.append(f'<img src="{img["src"]}" />')
                    content_found = True
                    if caption:
                        parts.append(f"<p><em>{caption.get_text(strip=True)}</em></p>")

            for paragraph in [p for p in article_tag.find_all("p") if len(p.get_text(strip=True)) > 20]:
                parts.append(f"<p>{paragraph.get_text(strip=True)}</p>")
                content_found = True

        if not parts or len(parts) <= 1:
            best_desc = ""
            best_thumb = ""
            for ld in self._iter_json_ld_objects(soup):
                image_url = self._extract_json_ld_image_url(ld)
                if image_url and not best_thumb:
                    best_thumb = image_url

                desc = ld.get("description", "")
                if isinstance(desc, str) and len(desc) > len(best_desc):
                    best_desc = desc
                    if image_url:
                        best_thumb = image_url

            if best_desc and len(best_desc) > 50:
                if best_thumb:
                    parts.insert(1, f'<img src="{best_thumb}" />')
                desc_soup = BeautifulSoup(best_desc, html_parser)
                desc_paragraphs = [p for p in desc_soup.find_all("p") if len(p.get_text(strip=True)) > 20]
                if desc_paragraphs:
                    for paragraph in desc_paragraphs:
                        parts.append(f"<p>{paragraph.get_text(strip=True)}</p>")
                    content_found = True
                else:
                    desc_text = unescape(desc_soup.get_text(" ", strip=True))
                    if len(desc_text) > 20:
                        parts.append(f"<p>{desc_text}</p>")
                        content_found = True

        entry.description = "\n".join(parts) if content_found else ""

    def _build_yahoo_article_entry(self, article_metadata: Metadata) -> FeedItem | None:
        entry = FeedItem(
            title=article_metadata.title,
            link=article_metadata.link,
            guid=article_metadata.guid or article_metadata.link,
            author="Reuters",
            created_time=article_metadata.created_time,
        )
        token = set_current_router(self.router_path)
        try:
            self._get_yahoo_article_content(article_metadata, entry)
        finally:
            reset_current_router(token)

        if entry.description:
            return entry

        logging.warning("Yahoo secondary source built empty content for %s", article_metadata.link)
        return None

    def refresh_from_yahoo(self) -> bool:
        soup = self._fetch_yahoo_page(self.yahoo_reuters_page)
        if soup is None:
            return False

        processed_any = False
        for category in self.combined_categories:
            parameter = {"category": category}
            article_list_key = self._metadata_list_cache_key(parameter)
            existing_metadata = read_metadata_list(article_list_key) or []
            incoming_metadata = self._parse_yahoo_articles(soup, category, existing_metadata)
            if not incoming_metadata:
                continue

            fetched_entries: dict[str, FeedItem] = {}
            for metadata in incoming_metadata:
                entry = self._build_yahoo_article_entry(metadata)
                if entry and entry.description:
                    fetched_entries[metadata.cache_key] = entry

            token = self._acquire_metadata_lock(category, "yahoo", len(incoming_metadata))
            if token is None:
                continue

            try:
                latest_metadata = read_metadata_list(article_list_key) or []
                final_metadata: list[Metadata] = []
                for metadata in incoming_metadata:
                    provisional_key = metadata.cache_key
                    metadata.cache_key = self._build_title_cache_key(
                        title=metadata.title,
                        created_time=metadata.created_time,
                        stable_source_identifier=metadata.link,
                        existing_metadata=latest_metadata,
                    )
                    cached_payload = read_feed_item_from_cache(metadata.cache_key)
                    if not (cached_payload and cached_payload.get("description")):
                        entry = fetched_entries.get(provisional_key)
                        if entry and entry.description:
                            entry.persist_to_cache(self.router_path, cache_key_override=metadata.cache_key)
                    final_metadata.append(metadata)

                merged_metadata = self._merge_yahoo_metadata(latest_metadata, final_metadata)
                replace_metadata_list(article_list_key, merged_metadata)
                logging.info(
                    "Reuters Yahoo-source published category=%s incoming=%d fetched_entries=%d",
                    category,
                    len(final_metadata),
                    len(fetched_entries),
                )
                processed_any = True
            finally:
                self._release_metadata_lock(category, token)

        return processed_any

    def _generate_response(self, last_build_time, feed_entries_list, parameter=None):
        feed_title = f"Reuters News - {parameter['category']}"
        feed_description = reuters_description
        feed_original_link = reuters_site_link
        feed = generate_feed_object_for_new_router(
            title=feed_title,
            link=feed_original_link,
            description=feed_description,
            language=language_english,
            last_build_time=last_build_time,
            feed_item_list=feed_entries_list,
        )
        return feed
