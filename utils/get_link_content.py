import requests
import urllib.request

from bs4 import BeautifulSoup

import constant.constants as c


def get_link_content_with_bs_no_params(link, parser=c.html_parser):
    soup = BeautifulSoup(requests.get(link).text, parser)
    return soup


def get_link_content_with_bs_and_header(link, parser, header):
    soup = BeautifulSoup(requests.get(link, headers=header).text, parser)
    return soup


def post_request_with_payload(link, parser, payload):
    soup = BeautifulSoup(requests.post(link, data=payload).text, parser)
    return soup


def load_json_response(link, header=None):
    response = requests.get(link, headers=header)
    return response.json()


def get_link_content_with_urllib_request(link):
    return BeautifulSoup(urllib.request.urlopen(link), 'lxml')
