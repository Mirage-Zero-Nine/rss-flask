import requests
from bs4 import BeautifulSoup

import constant.constants as c


def get_link_content_with_bs_no_params(link, parser=c.html_parser):
    soup = BeautifulSoup(requests.get(link).text, parser)
    return soup


def get_link_content_with_bs_and_header(link, parser, header):
    soup = BeautifulSoup(requests.get(link, headers=header).text, parser)
    return soup
