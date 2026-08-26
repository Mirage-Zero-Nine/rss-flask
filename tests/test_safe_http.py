import socket

import pytest
import requests

from utils import safe_http


def _address_record(address: str):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sockaddr = (address, 443, 0, 0) if family == socket.AF_INET6 else (address, 443)
    return (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr)


def _response(url: str, *, status: int = 200, location: str | None = None, content: bytes = b"ok"):
    response = requests.Response()
    response.status_code = status
    response.url = url
    response._content = content
    response._content_consumed = True
    if location is not None:
        response.headers["location"] = location
    return response


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.32.5.206",
        "172.19.0.2",
        "192.168.1.1",
        "100.64.0.1",
        "169.254.169.254",
        "::1",
        "fc00::1",
        "fe80::1",
        "::ffff:10.32.5.206",
    ],
)
def test_validate_public_url_blocks_non_public_addresses(monkeypatch, address):
    monkeypatch.setattr(
        safe_http.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [_address_record(address)],
    )

    with pytest.raises(safe_http.UnsafeUrlError, match="non-public"):
        safe_http.validate_public_url("https://attacker.example/article")


def test_validate_public_url_blocks_mixed_public_and_private_dns(monkeypatch):
    monkeypatch.setattr(
        safe_http.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [_address_record("93.184.216.34"), _address_record("10.32.5.206")],
    )

    with pytest.raises(safe_http.UnsafeUrlError, match="10.32.5.206"):
        safe_http.validate_public_url("https://attacker.example/article")


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "https://user:password@example.com/",
        "https:///missing-host",
    ],
)
def test_validate_public_url_rejects_unsafe_url_shapes(url):
    with pytest.raises(safe_http.UnsafeUrlError):
        safe_http.validate_public_url(url)


def test_safe_get_allows_public_destination_without_automatic_redirects(monkeypatch):
    monkeypatch.setattr(
        safe_http.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [_address_record("93.184.216.34")],
    )
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _response(url)

    monkeypatch.setattr(safe_http.requests, "get", fake_get)

    response = safe_http.safe_get("https://example.com/article", timeout=4)

    assert response.text == "ok"
    assert calls == [
        ("https://example.com/article", {"allow_redirects": False, "timeout": 4})
    ]


def test_safe_get_blocks_redirect_to_home_network_before_second_request(monkeypatch):
    def fake_resolve(hostname, *_args, **_kwargs):
        address = "93.184.216.34" if hostname == "public.example" else "10.32.5.206"
        return [_address_record(address)]

    monkeypatch.setattr(safe_http.socket, "getaddrinfo", fake_resolve)
    calls = []

    def fake_get(url, **_kwargs):
        calls.append(url)
        return _response(url, status=302, location="http://rss.home/admin")

    monkeypatch.setattr(safe_http.requests, "get", fake_get)

    with pytest.raises(safe_http.UnsafeUrlError, match="10.32.5.206"):
        safe_http.safe_get("https://public.example/feed")

    assert calls == ["https://public.example/feed"]


def test_safe_get_validates_each_public_redirect(monkeypatch):
    monkeypatch.setattr(
        safe_http.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [_address_record("93.184.216.34")],
    )
    calls = []

    def fake_get(url, **_kwargs):
        calls.append(url)
        if len(calls) == 1:
            return _response(url, status=301, location="/final")
        return _response(url, content=b"done")

    monkeypatch.setattr(safe_http.requests, "get", fake_get)

    response = safe_http.safe_get("https://public.example/start")

    assert response.content == b"done"
    assert calls == ["https://public.example/start", "https://public.example/final"]
