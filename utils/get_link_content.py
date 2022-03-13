import requests
from bs4 import BeautifulSoup


def get_link_content_with_bs_no_params(link, parser):
    soup = BeautifulSoup(requests.get(link).text, parser)
    return soup


def get_link_content_with_bs_and_header(link, parser, header):
    soup = BeautifulSoup(requests.get(link, headers=header).text, parser)
    return soup
