"""Outbound HTTP helpers pinned to validated public destination addresses.

Feed and article URLs are untrusted. Each hop resolves once; the transport sees
only those validated IP literals, while HTTP Host and TLS authentication retain
the original hostname. Neither transport uses environment-configured proxies.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import partial
from urllib.parse import urljoin, urlsplit

import feedparser
import requests


DEFAULT_REQUEST_TIMEOUT_SECONDS = 30
MAX_REDIRECTS = 5
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
_SENSITIVE_HEADERS = {"authorization", "proxy-authorization", "cookie"}
IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class UnsafeUrlError(requests.RequestException):
    """Raised when an outbound request could bypass the destination policy."""


@dataclass(frozen=True)
class _PublicTarget:
    scheme: str
    hostname: str
    port: int
    addresses: tuple[IPAddress, ...]

    @property
    def authority(self) -> str:
        host = f"[{self.hostname}]" if ":" in self.hostname else self.hostname
        default_port = 443 if self.scheme == "https" else 80
        return host if self.port == default_port else f"{host}:{self.port}"


def _resolved_addresses(hostname: str, port: int) -> set[IPAddress]:
    try:
        records = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise requests.ConnectionError(f"could not resolve outbound host {hostname!r}: {exc}") from exc

    addresses: set[IPAddress] = set()
    for record in records:
        raw_address = record[4][0].split("%", 1)[0]
        try:
            addresses.add(ipaddress.ip_address(raw_address))
        except ValueError as exc:
            raise UnsafeUrlError(f"resolver returned an invalid address for {hostname!r}") from exc
    if not addresses:
        raise requests.ConnectionError(f"outbound host {hostname!r} resolved to no addresses")
    return addresses


def _resolve_public_url(url: str) -> _PublicTarget:
    if not isinstance(url, str) or not url.strip():
        raise UnsafeUrlError("outbound URL must be a non-empty string")
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise UnsafeUrlError("invalid outbound URL") from exc
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise UnsafeUrlError(f"outbound URL scheme is not allowed: {parsed.scheme!r}")
    if not parsed.hostname or "%" in parsed.hostname:
        raise UnsafeUrlError("outbound URL has an invalid hostname")
    if parsed.username is not None or parsed.password is not None:
        raise UnsafeUrlError("credentials in outbound URLs are not allowed")
    if port == 0:
        raise UnsafeUrlError("outbound URL has an invalid port")

    destination_port = port or (443 if scheme == "https" else 80)
    addresses = _resolved_addresses(parsed.hostname, destination_port)
    for address in addresses:
        if not address.is_global or address.is_multicast:
            raise UnsafeUrlError(
                f"outbound URL resolves to a non-public address: {parsed.hostname!r} -> {address}"
            )
    # Keep the full validated answer for connection fallback; never re-resolve
    # the hostname when an address is unreachable. Prefer IPv4 on dual-stack hosts.
    return _PublicTarget(scheme, parsed.hostname, destination_port,
                         tuple(sorted(addresses, key=lambda value: (value.version, int(value)))))


def validate_public_url(url: str) -> None:
    """Validate a URL; fetching must also pin the validated DNS answer."""
    _resolve_public_url(url)


class _PinnedHTTPAdapter(requests.adapters.HTTPAdapter):
    """Requests transport using IP-address pools with original TLS identity."""

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        if proxies:
            raise UnsafeUrlError("outbound proxies are not allowed")
        if not verify:
            raise UnsafeUrlError("outbound TLS certificate verification cannot be disabled")
        target = _resolve_public_url(request.url)
        request.headers["Host"] = target.authority
        self._target = target
        last_error = None
        for address in target.addresses:
            self._address = str(address)
            try:
                return super().send(request, stream=stream, timeout=timeout,
                                    verify=verify, cert=cert, proxies={})
            except requests.exceptions.SSLError:
                raise
            except (requests.ConnectionError, requests.ConnectTimeout) as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        if proxies:
            raise UnsafeUrlError("outbound proxies are not allowed")
        host_params, pool_kwargs = self.build_connection_pool_key_attributes(request, verify, cert)
        # urllib3 may call getaddrinfo for this IP literal, but it never receives
        # the attacker-controlled DNS name for the socket connection.
        host_params["host"] = self._address
        host_params["port"] = self._target.port
        if self._target.scheme == "https":
            pool_kwargs["server_hostname"] = self._target.hostname
            pool_kwargs["assert_hostname"] = self._target.hostname
        return self.poolmanager.connection_from_host(**host_params, pool_kwargs=pool_kwargs)


def _origin(url: str) -> tuple[str, str | None, int]:
    parsed = urlsplit(url)
    return parsed.scheme.lower(), parsed.hostname, parsed.port or (443 if parsed.scheme.lower() == "https" else 80)


def _redirect_headers(headers, current_url: str, next_url: str) -> dict[str, str]:
    cross_origin = _origin(current_url) != _origin(next_url)
    return {key: value for key, value in (headers or {}).items()
            if key.lower() != "host" and not (cross_origin and key.lower() in _SENSITIVE_HEADERS)}


def _redirect_target(current_url: str, location: str) -> str:
    target = urljoin(current_url, location)
    if urlsplit(current_url).scheme.lower() == "https" and urlsplit(target).scheme.lower() == "http":
        raise UnsafeUrlError("HTTPS to HTTP redirect downgrade is not allowed")
    return target


def safe_get(url: str, *, max_redirects: int = MAX_REDIRECTS, **kwargs) -> requests.Response:
    """GET through a pinned transport, validating every redirect independently."""
    kwargs.pop("allow_redirects", None)
    kwargs.setdefault("timeout", DEFAULT_REQUEST_TIMEOUT_SECONDS)
    current_url = url
    visited: set[str] = set()
    history: list[requests.Response] = []
    with requests.Session() as session:
        # Disables proxy variables, .netrc authentication and CA-bundle overrides.
        session.trust_env = False
        adapter = _PinnedHTTPAdapter(max_retries=0)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        for redirect_count in range(max_redirects + 1):
            if current_url in visited:
                raise requests.TooManyRedirects("outbound redirect loop detected")
            visited.add(current_url)
            response = session.get(current_url, allow_redirects=False, **kwargs)
            location = response.headers.get("location")
            if response.status_code not in _REDIRECT_STATUSES or not location:
                response.history = history
                return response
            if redirect_count >= max_redirects:
                response.close()
                raise requests.TooManyRedirects(f"exceeded {max_redirects} outbound redirects")
            response.close()
            next_url = _redirect_target(response.url or current_url, location)
            history.append(response)
            kwargs["headers"] = _redirect_headers(kwargs.get("headers"), current_url, next_url)
            # Query parameters belong to the initial request, not redirect targets.
            kwargs.pop("params", None)
            if _origin(current_url) != _origin(next_url):
                kwargs.pop("auth", None)
                kwargs.pop("cookies", None)
            current_url = next_url
    raise requests.TooManyRedirects(f"exceeded {max_redirects} outbound redirects")


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _connect_validated(target: _PublicTarget, timeout, source_address=None):
    last_error = None
    for address in target.addresses:
        try:
            # Only validated numeric addresses reach the stdlib socket helper.
            return socket.create_connection((str(address), target.port), timeout, source_address)
        except OSError as exc:
            last_error = exc
    assert last_error is not None
    raise last_error


def _stdlib_connection(target: _PublicTarget, host: str, **kwargs):
    connection_type = http.client.HTTPSConnection if target.scheme == "https" else http.client.HTTPConnection
    connection = connection_type(host, **kwargs)
    # HTTPConnection.connect calls this factory; HTTPSConnection subsequently
    # wraps the socket with its original hostname and standard verified context.
    connection._create_connection = lambda _address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None: _connect_validated(target, timeout, source_address)
    return connection


class _PinnedHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        target = _resolve_public_url(req.full_url)
        req.add_unredirected_header("Host", target.authority)
        return self.do_open(partial(_stdlib_connection, target), req)


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        target = _resolve_public_url(req.full_url)
        req.add_unredirected_header("Host", target.authority)
        return self.do_open(partial(_stdlib_connection, target), req, context=self._context)


def safe_urllib_get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    max_redirects: int = MAX_REDIRECTS,
) -> bytes:
    """Pinned GET retaining the stdlib TLS client used by some upstreams."""
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), _NoRedirectHandler(),
        _PinnedHTTPHandler(), _PinnedHTTPSHandler(),
    )
    current_url = url
    current_headers = dict(headers or {})
    visited: set[str] = set()
    for redirect_count in range(max_redirects + 1):
        if current_url in visited:
            raise requests.TooManyRedirects("outbound redirect loop detected")
        visited.add(current_url)
        # Reject non-HTTP schemes before urllib can select a file/FTP handler.
        parsed = urlsplit(current_url)
        if parsed.scheme.lower() not in {"http", "https"}:
            raise UnsafeUrlError("outbound URL scheme is not allowed")
        request = urllib.request.Request(current_url, headers=current_headers)
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
                raise requests.TooManyRedirects(f"exceeded {max_redirects} outbound redirects")
            next_url = _redirect_target(response.geturl() or current_url, location)
            current_headers = _redirect_headers(current_headers, current_url, next_url)
            current_url = next_url
        finally:
            response.close()
    raise requests.TooManyRedirects(f"exceeded {max_redirects} outbound redirects")


def safe_parse_feed(url: str):
    """Fetch an RSS/Atom document safely, then parse downloaded bytes."""
    response = safe_get(url)
    return feedparser.parse(response.content)
