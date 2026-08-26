from bs4 import BeautifulSoup

from utils.log_context import log_external_fetch
from utils.router_constants import html_parser
from utils.safe_http import DEFAULT_REQUEST_TIMEOUT_SECONDS, safe_get, safe_urllib_get


def get_link_content_with_bs_no_params(link, parser=html_parser):
    log_external_fetch("requests.get", link, parser=parser)
    return BeautifulSoup(safe_get(link, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).text, parser)


def get_link_content_with_utf8_decode(link, parser=html_parser):
    log_external_fetch("requests.get", link, parser=parser, decode="utf-8")
    return BeautifulSoup(safe_get(link, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).content.decode('utf-8'), parser)


def get_link_content_with_header_and_empty_cookie(link, header, parser=html_parser):
    # pass an empty cookie
    log_external_fetch("requests.get", link, parser=parser, headers=True, cookies="empty")
    return BeautifulSoup(
        safe_get(link, headers=header, cookies={}, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).text,
        parser,
    )


def get_link_content_with_urllib_request(link, headers=None, parser='lxml'):
    log_external_fetch(
        "urllib.request.urlopen",
        link,
        timeout=15,
        parser=parser,
        headers=bool(headers),
    )
    return BeautifulSoup(
        safe_urllib_get(link, headers=headers, timeout=15),
        parser,
    )


def load_json_response(link, **kwargs):
    log_external_fetch("requests.get", link, response="json", **kwargs)
    kwargs.setdefault("timeout", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    return safe_get(link, **kwargs).json()
