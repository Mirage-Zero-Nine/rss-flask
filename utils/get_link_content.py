import requests
import urllib.request

from bs4 import BeautifulSoup

from utils.log_context import log_external_fetch
from utils.router_constants import html_parser

DEFAULT_REQUEST_TIMEOUT_SECONDS = 30


def get_link_content_with_bs_no_params(link, parser=html_parser):
    log_external_fetch("requests.get", link, parser=parser)
    return BeautifulSoup(requests.get(link, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).text, parser)


def get_link_content_with_utf8_decode(link, parser=html_parser):
    log_external_fetch("requests.get", link, parser=parser, decode="utf-8")
    return BeautifulSoup(requests.get(link, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).content.decode('utf-8'), parser)


def get_link_content_with_header_and_empty_cookie(link, header, parser=html_parser):
    # pass an empty cookie
    log_external_fetch("requests.get", link, parser=parser, headers=True, cookies="empty")
    return BeautifulSoup(
        requests.get(link, headers=header, cookies={}, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).text,
        parser,
    )


def get_link_content_with_urllib_request(link):
    log_external_fetch("urllib.request.urlopen", link, timeout=15, parser="lxml")
    return BeautifulSoup(urllib.request.urlopen(link, timeout=15), 'lxml')


def load_json_response(link, **kwargs):
    log_external_fetch("requests.get", link, response="json", **kwargs)
    kwargs.setdefault("timeout", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    return requests.get(link, **kwargs).json()
