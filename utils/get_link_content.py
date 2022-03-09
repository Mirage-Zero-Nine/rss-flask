import requests
from bs4 import BeautifulSoup


def get_link_content_with_bs_no_params(link, parser):
    soup = BeautifulSoup(requests.get(link).text, parser)
    return soup
