import logging
import urllib.request

import requests
from bs4 import BeautifulSoup

from rss_flask.settings import HTML_PARSER
from utils.log_context import format_router_log_prefix


class InvalidJsonResponseError(RuntimeError):
    pass


def _log_request(method, link, extra=""):
    suffix = f" {extra}" if extra else ""
    logging.info("%s outbound_request method=%s url=%s%s", format_router_log_prefix(), method, link, suffix)


def get_link_content_with_bs_no_params(link, parser=HTML_PARSER):
    _log_request("GET", link)
    return BeautifulSoup(requests.get(link).text, parser)


def get_link_content_with_utf8_decode(link, parser=HTML_PARSER):
    _log_request("GET", link, "decode=utf-8")
    return BeautifulSoup(requests.get(link).content.decode("utf-8"), parser)


def get_content_with_utf8_decode_and_disable_verification(link, parser=HTML_PARSER):
    _log_request("GET", link, "decode=utf-8 verify=false")
    return BeautifulSoup(requests.get(link, verify=False).content.decode("utf-8"), parser)


def get_link_content_with_header_and_empty_cookie(link, header, parser=HTML_PARSER):
    _log_request("GET", link, "headers=true cookies=empty")
    return BeautifulSoup(requests.get(link, headers=header, cookies={}).text, parser)


def get_link_content_with_urllib_request(link):
    _log_request("GET", link, "client=urllib timeout=15")
    return BeautifulSoup(urllib.request.urlopen(link, timeout=15), "lxml")


def load_json_response(link, **kwargs):
    _log_request("GET", link, "response=json")
    response = requests.get(link, **kwargs)
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        preview = response.text[:300].replace("\n", " ")
        raise InvalidJsonResponseError(
            "%s invalid_json_response status=%s url=%s body_preview=%s error=%s"
            % (
                format_router_log_prefix(),
                response.status_code,
                link,
                preview,
                exc,
            )
        ) from exc
