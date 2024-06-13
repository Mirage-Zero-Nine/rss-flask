import requests
import urllib.request

from bs4 import BeautifulSoup

from utils.router_constants import html_parser


def get_link_content_with_bs_no_params(link, parser=html_parser):
    return BeautifulSoup(requests.get(link).text, parser)


def get_link_content_with_utf8_decode(link, parser=html_parser):
    return BeautifulSoup(requests.get(link).content.decode('utf-8'), parser)


def get_content_with_utf8_decode_and_disable_verification(link, parser=html_parser):
    return BeautifulSoup(requests.get(link, verify=False).content.decode('utf-8'), parser)


def get_link_content_with_header_and_empty_cookie(link, header, parser=html_parser):
    # pass an empty cookie
    return BeautifulSoup(requests.get(link, headers=header, cookies={}).text, parser)


def get_link_content_with_urllib_request(link):
    return BeautifulSoup(urllib.request.urlopen(link), 'lxml')


def load_json_response(link, **kwargs):
    return requests.get(link, **kwargs).json()
