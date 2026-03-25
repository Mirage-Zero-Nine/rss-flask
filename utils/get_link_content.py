from bs4 import BeautifulSoup

from utils.http_client import get_content, get_response, get_text
from utils.router_constants import html_parser


def get_link_content_with_bs_no_params(link, parser=html_parser):
    return BeautifulSoup(get_text(link), parser)


def get_link_content_with_utf8_decode(link, parser=html_parser):
    return BeautifulSoup(get_content(link).decode('utf-8'), parser)


def get_content_with_utf8_decode_and_disable_verification(link, parser=html_parser):
    return BeautifulSoup(get_content(link, verify=False).decode('utf-8'), parser)


def get_link_content_with_header_and_empty_cookie(link, header, parser=html_parser):
    # pass an empty cookie
    return BeautifulSoup(get_text(link, headers=header, cookies={}), parser)


def get_link_content_with_urllib_request(link):
    return BeautifulSoup(get_content(link), 'lxml')


def load_json_response(link, **kwargs):
    return get_response(link, **kwargs).json()
