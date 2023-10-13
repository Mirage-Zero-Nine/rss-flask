import requests
import urllib.request

from bs4 import BeautifulSoup

from utils.router_constants import html_parser


def get_link_content_with_bs_no_params(link, parser=html_parser):
    soup = BeautifulSoup(requests.get(link).text, parser)
    return soup


def get_link_content_with_utf8_decode(link, parser=html_parser):
    return BeautifulSoup(requests.get(link).content.decode('utf-8'), parser)


def get_link_content_with_bs_and_header(link, parser, header):
    soup = BeautifulSoup(requests.get(link, headers=header, cookies={"sspai_cross_token": "logout"}).text, parser)
    return soup


def post_request_with_payload(link, parser, payload):
    soup = BeautifulSoup(requests.post(link, data=payload).text, parser)
    return soup


def load_json_response(link, header=None):
    response = requests.get(link, headers=header)
    return response.json()


def get_link_content_with_urllib_request(link):
    return BeautifulSoup(urllib.request.urlopen(link), 'lxml')


def get_link_content_with_html_entity(link):
    return BeautifulSoup(link, 'lxml', from_encoding='utf-8')