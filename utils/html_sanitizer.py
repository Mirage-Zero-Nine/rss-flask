"""Sanitize untrusted article HTML at the RSS boundary, including old cache data.

Use an HTML5 sanitizer rather than scraping-parser tag removal as a security
boundary. No network requests or cache writes belong in this module.
"""

import re
from functools import partial
from urllib.parse import urljoin, urlsplit

import nh3


_TAGS = {
    "a", "abbr", "article", "audio", "b", "blockquote", "br", "caption",
    "code", "col", "colgroup", "dd", "del", "details", "div", "dl", "dt",
    "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "iframe", "img", "ins", "kbd", "li", "mark", "ol", "p",
    "pre", "q", "s", "samp", "section", "small", "source", "span", "strong",
    "sub", "summary", "sup", "table", "tbody", "td", "tfoot", "th", "thead",
    "time", "tr", "u", "ul", "var", "video", "wbr",
}
_ATTRIBUTES = {
    "*": {"title", "lang", "dir"},
    "a": {"href"},
    "audio": {"src"},
    "blockquote": {"cite"},
    "col": {"span"},
    "colgroup": {"span"},
    "del": {"datetime"},
    "iframe": {"src", "width", "height"},
    "img": {"src", "alt", "width", "height"},
    "ins": {"datetime"},
    "li": {"value"},
    "ol": {"start", "reversed", "type"},
    "q": {"cite"},
    "source": {"src", "type"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "time": {"datetime"},
    "video": {"src", "poster", "width", "height"},
}
_EMBED_PATHS = {
    "player.vimeo.com": re.compile(r"/video/[0-9]+/?\Z"),
    "www.youtube.com": re.compile(r"/embed/[A-Za-z0-9_-]+/?\Z"),
    "www.youtube-nocookie.com": re.compile(r"/embed/[A-Za-z0-9_-]+/?\Z"),
}
_INVALID_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
_URL_WHITESPACE = re.compile(r"[\x00-\x20\x7f-\x9f]")


def _safe_url(value: str, base_url: str | None, *, media: bool, iframe: bool) -> str | None:
    # Reject ambiguous URL spellings before urllib and the reader's URL parser
    # have a chance to disagree. nh3 has already decoded HTML entities.
    value = value.strip()
    if not value or _URL_WHITESPACE.search(value) or "\\" in value:
        return None
    try:
        if value.startswith("//"):
            value = "https:" + value
        elif base_url:
            value = urljoin(base_url, value)
        parsed = urlsplit(value)
        if not media and parsed.scheme in {"mailto", "tel"}:
            return value
        if parsed.scheme not in ({"https"} if media else {"https", "http"}):
            return None
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return None
        # Force validation of malformed/out-of-range ports as well.
        port = parsed.port
        if iframe:
            path_rule = _EMBED_PATHS.get(parsed.hostname)
            if port not in {None, 443} or path_rule is None or not path_rule.fullmatch(parsed.path):
                return None
    except ValueError:
        return None
    return value


def _filter_attribute(tag: str, attribute: str, value: str, *, base_url: str | None) -> str | None:
    if attribute in {"href", "src", "poster", "cite"}:
        return _safe_url(value, base_url, media=attribute in {"src", "poster"}, iframe=tag == "iframe")
    if attribute in {"width", "height", "colspan", "rowspan", "span"}:
        return value if len(value) <= 4 and value.isascii() and value.isdigit() and 0 < int(value) <= 8192 else None
    return value


def sanitize_article_html(description: object | None, base_url: str | None = None) -> str | None:
    """Return reader-safe HTML without changing the source FeedItem or cache.

    Article structure, HTTPS media, and sandboxed Vimeo/YouTube players survive.
    CSS, scripts, event handlers, forms, SVG/MathML, srcdoc, data URLs, and
    insecure embedded media do not. Ordinary HTTP links remain clickable.
    """
    if description is None:
        return None
    # XML 1.0 forbids these even as escaped text; surrogates also cannot cross
    # nh3's Python/Rust boundary. Keep normal Unicode, tabs and line breaks.
    html = _INVALID_XML.sub("", str(description))
    safe_base = _safe_url(base_url, None, media=False, iframe=False) if base_url else None
    if safe_base and urlsplit(safe_base).scheme not in {"http", "https"}:
        safe_base = None
    result = nh3.clean(
        html,
        tags=_TAGS,
        attributes=_ATTRIBUTES,
        clean_content_tags={"script", "style", "svg", "math", "template", "object", "embed"},
        attribute_filter=partial(_filter_attribute, base_url=safe_base),
        url_schemes={"https", "http", "mailto", "tel"},
        strip_comments=True,
        link_rel="noopener noreferrer",
        set_tag_attribute_values={
            "iframe": {
                "sandbox": "allow-scripts allow-same-origin allow-presentation",
                "referrerpolicy": "no-referrer",
                "allowfullscreen": "",
            },
            "audio": {"controls": "", "preload": "none"},
            "video": {"controls": "", "preload": "none", "playsinline": ""},
        },
    )
    # Character references can introduce forbidden XML characters during HTML
    # parsing, so apply the XML filter after sanitization too.
    return _INVALID_XML.sub("", result)
