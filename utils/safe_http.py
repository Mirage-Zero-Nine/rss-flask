"""Outbound HTTP helpers that prevent requests to non-public networks.

Feed and article URLs are partly controlled by upstream content.  Treat every
URL, including every redirect target, as untrusted before opening a socket.
"""

from __future__ import annotations

import ipaddress
import socket
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit

import feedparser
import requests


DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
MAX_REDIRECTS = 5
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


class UnsafeUrlError(requests.RequestException):
    """Raised when an outbound URL could reach a non-public destination."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Expose redirects so each target can be validated before it is opened."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _resolved_addresses(hostname: str, port: int) -> set[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise requests.ConnectionError(f"could not resolve outbound host {hostname!r}: {exc}") from exc

    addresses: set[ipaddress.IPv4Address | ipaddress.IPv6Address] = set()
    for record in records:
        raw_address = record[4][0].split("%", 1)[0]
        try:
            addresses.add(ipaddress.ip_address(raw_address))
        except ValueError as exc:
            raise UnsafeUrlError(f"resolver returned an invalid address for {hostname!r}") from exc

    if not addresses:
        raise requests.ConnectionError(f"outbound host {hostname!r} resolved to no addresses")
    return addresses


def validate_public_url(url: str) -> None:
    """Reject URLs that are not HTTP(S) or resolve outside the public Internet."""

    if not isinstance(url, str) or not url.strip():
        raise UnsafeUrlError("outbound URL must be a non-empty string")

    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrlError(f"invalid outbound URL: {url!r}") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeUrlError(f"outbound URL scheme is not allowed: {parsed.scheme!r}")
    if not parsed.hostname:
        raise UnsafeUrlError("outbound URL has no hostname")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("credentials in outbound URLs are not allowed")

    destination_port = port or (443 if parsed.scheme.lower() == "https" else 80)
    for address in _resolved_addresses(parsed.hostname, destination_port):
        # is_global excludes loopback, RFC1918/ULA, link-local, CGNAT,
        # documentation, reserved and unspecified ranges.  Multicast is marked
        # global by some Python versions, so reject it explicitly.
        if not address.is_global or address.is_multicast:
            raise UnsafeUrlError(
                f"outbound URL resolves to a non-public address: {parsed.hostname!r} -> {address}"
            )


def safe_get(url: str, *, max_redirects: int = MAX_REDIRECTS, **kwargs) -> requests.Response:
    """Perform a GET after validating the initial URL and each redirect hop."""

    kwargs.pop("allow_redirects", None)
    kwargs.setdefault("timeout", DEFAULT_REQUEST_TIMEOUT_SECONDS)

    current_url = url
    visited: set[str] = set()
    for redirect_count in range(max_redirects + 1):
        validate_public_url(current_url)
        if current_url in visited:
            raise requests.TooManyRedirects(f"redirect loop detected for {current_url}")
        visited.add(current_url)

        response = requests.get(current_url, allow_redirects=False, **kwargs)
        location = response.headers.get("location")
        if response.status_code not in _REDIRECT_STATUSES or not location:
            return response

        if redirect_count >= max_redirects:
            response.close()
            raise requests.TooManyRedirects(f"exceeded {max_redirects} redirects for {url}")

        next_url = urljoin(response.url or current_url, location)
        response.close()
        current_url = next_url

    raise requests.TooManyRedirects(f"exceeded {max_redirects} redirects for {url}")


def safe_urllib_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    max_redirects: int = MAX_REDIRECTS,
) -> bytes:
    """Fetch bytes with urllib while validating the URL and every redirect.

    This is kept separate from ``safe_get`` because some upstream bot filters
    treat Requests' TLS client differently from Python's standard-library
    client even when both send the same HTTP headers.
    """

    opener = urllib.request.build_opener(_NoRedirectHandler())
    current_url = url
    visited: set[str] = set()
    for redirect_count in range(max_redirects + 1):
        validate_public_url(current_url)
        if current_url in visited:
            raise requests.TooManyRedirects(f"redirect loop detected for {current_url}")
        visited.add(current_url)

        request = urllib.request.Request(current_url, headers=headers or {})
        try:
            response = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            location = exc.headers.get("location")
            if exc.code not in _REDIRECT_STATUSES or not location:
                raise
            response = exc

        try:
            status = response.getcode()
            location = response.headers.get("location")
            if status not in _REDIRECT_STATUSES or not location:
                return response.read()

            if redirect_count >= max_redirects:
                raise requests.TooManyRedirects(f"exceeded {max_redirects} redirects for {url}")

            current_url = urljoin(response.geturl() or current_url, location)
        finally:
            response.close()

    raise requests.TooManyRedirects(f"exceeded {max_redirects} redirects for {url}")


def safe_parse_feed(url: str):
    """Fetch an RSS/Atom document safely, then parse the downloaded bytes."""

    response = safe_get(url)
    return feedparser.parse(response.content)
