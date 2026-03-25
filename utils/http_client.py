import logging

import requests


DEFAULT_TIMEOUT_SECONDS = 15
_session = requests.Session()


def get_response(url, *, timeout=DEFAULT_TIMEOUT_SECONDS, **kwargs):
    return _session.get(url, timeout=timeout, **kwargs)


def get_text(url, *, timeout=DEFAULT_TIMEOUT_SECONDS, **kwargs):
    response = get_response(url, timeout=timeout, **kwargs)
    return response.text


def get_content(url, *, timeout=DEFAULT_TIMEOUT_SECONDS, **kwargs):
    response = get_response(url, timeout=timeout, **kwargs)
    return response.content


def get_json(url, *, timeout=DEFAULT_TIMEOUT_SECONDS, **kwargs):
    response = get_response(url, timeout=timeout, **kwargs)
    return response.json()


def log_json_decode_error(context, response, exc):
    snippet = response.text.replace("\n", " ")[:200]
    logging.error(
        "%s (status=%s url=%s). Error: %s. Payload snippet: %s",
        context,
        response.status_code,
        response.url,
        exc,
        snippet,
    )
