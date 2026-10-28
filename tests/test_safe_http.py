import collections
import ipaddress
import socket
import ssl
from io import BytesIO
from types import SimpleNamespace

import pytest
import requests
import urllib3.connection

from utils import safe_http


def _address_record(address, port=443):
    family = socket.AF_INET6 if ":" in address else socket.AF_INET
    sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    return family, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", sockaddr


@pytest.mark.parametrize("address", [
    "127.0.0.1", "10.0.0.10", "172.16.0.20", "192.168.1.1", "100.64.0.1",
    "169.254.169.254", "0.0.0.0", "224.0.0.1", "192.0.2.1", "::1",
    "fc00::1", "fe80::1", "::ffff:10.0.0.10", "ff02::1", "::",
])
def test_validate_public_url_blocks_non_public_addresses(monkeypatch, address):
    monkeypatch.setattr(safe_http.socket, "getaddrinfo", lambda *_a, **_kw: [_address_record(address)])
    with pytest.raises(safe_http.UnsafeUrlError, match="non-public"):
        safe_http.validate_public_url("https://attacker.example/article")


def test_validate_public_url_blocks_mixed_public_and_private_dns(monkeypatch):
    monkeypatch.setattr(safe_http.socket, "getaddrinfo", lambda *_a, **_kw: [
        _address_record("93.184.216.34"), _address_record("10.0.0.10")])
    with pytest.raises(safe_http.UnsafeUrlError, match="10.0.0.10"):
        safe_http.validate_public_url("https://attacker.example/article")


@pytest.mark.parametrize("url", [
    "file:///etc/passwd", "ftp://example.com/file", "https://user:password@example.com/",
    "https:///missing-host", "https://example.com:0/", "https://example.com:99999/",
    "https://[fe80::1%eth0]/", "https://example.com%2eattacker.test/",
])
def test_validate_public_url_rejects_unsafe_url_shapes(url):
    with pytest.raises(safe_http.UnsafeUrlError):
        safe_http.validate_public_url(url)


def _wire_response(body=b"done", status=200, headers=None):
    fields = {"Content-Length": str(len(body)), "Content-Type": "text/plain; charset=utf-8", **(headers or {})}
    head = f"HTTP/1.1 {status} Response\r\n" + "".join(f"{k}: {v}\r\n" for k, v in fields.items())
    return head.encode("ascii") + b"\r\n" + body


@pytest.fixture
def network(monkeypatch):
    """Run the real HTTP clients with a deterministic in-memory socket boundary."""
    state = SimpleNamespace(dns_calls=[], connections=[], requests=[], tls_calls=[],
                            responses=collections.deque(), answers={}, fail_addresses=set())

    def resolve(host, port, *args, **kwargs):
        state.dns_calls.append(host)
        try:
            ipaddress.ip_address(host)
        except ValueError:
            answers = state.answers.get(host, ["93.184.216.34"])
        else:
            answers = [host]
        return [_address_record(ip, port) for ip in answers]

    class FakeSocket:
        def __init__(self, *args, **kwargs):
            self.sent = bytearray()
            self.timeout = None
        def settimeout(self, value):
            self.timeout = value
        def gettimeout(self):
            return self.timeout
        def setsockopt(self, *args):
            pass
        def bind(self, *args):
            pass
        def connect(self, address):
            state.connections.append(address)
            if address[0] in state.fail_addresses:
                raise ConnectionRefusedError("fixture refused connection")
        def sendall(self, data):
            self.sent.extend(data)
        def makefile(self, *args, **kwargs):
            state.requests.append(bytes(self.sent))
            return BytesIO(state.responses.popleft() if state.responses else _wire_response())
        def close(self):
            pass
        def fileno(self):
            return -1

    def requests_tls(sock, **kwargs):
        state.tls_calls.append(kwargs)
        return sock, True

    def stdlib_tls(context, sock, **kwargs):
        state.tls_calls.append({**kwargs, "check_hostname": context.check_hostname,
                                "verify_mode": context.verify_mode})
        return sock

    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    monkeypatch.setattr(socket, "socket", FakeSocket)
    monkeypatch.setattr(urllib3.connection, "_ssl_wrap_socket_and_match_hostname", requests_tls)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", stdlib_tls)
    return state


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_rebinding_cannot_change_connection_destination(network, monkeypatch, transport):
    resolver = socket.getaddrinfo
    lookups = 0
    def rebind(host, port, *args, **kwargs):
        nonlocal lookups
        if host == "attacker.example":
            lookups += 1
            # A second unchecked hostname lookup would connect to the home network.
            network.answers[host] = ["93.184.216.34" if lookups == 1 else "10.0.0.10"]
        return resolver(host, port, *args, **kwargs)
    monkeypatch.setattr(socket, "getaddrinfo", rebind)
    if transport == "requests":
        response = safe_http.safe_get("https://attacker.example/article", timeout=4)
        assert response.content == b"done"
        assert response.url == "https://attacker.example/article"
    else:
        assert safe_http.safe_urllib_get("https://attacker.example/article", timeout=4) == b"done"
    assert lookups == 1
    assert network.connections == [("93.184.216.34", 443)]
    assert b"Host: attacker.example\r\n" in network.requests[0]
    assert network.tls_calls[0]["server_hostname"] == "attacker.example"
    if transport == "requests":
        assert network.tls_calls[0]["assert_hostname"] == "attacker.example"
        assert network.tls_calls[0]["cert_reqs"] in {"CERT_REQUIRED", ssl.CERT_REQUIRED}
    else:
        assert network.tls_calls[0]["check_hostname"] is True
        assert network.tls_calls[0]["verify_mode"] == ssl.CERT_REQUIRED


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_redirect_to_private_host_is_blocked_before_socket(network, transport):
    network.responses.append(_wire_response(status=302, headers={"Location": "https://private.example/admin"}))
    network.answers["private.example"] = ["10.0.0.10"]
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    with pytest.raises(safe_http.UnsafeUrlError, match="non-public"):
        get("https://public.example/start")
    assert len(network.connections) == 1
    assert network.dns_calls.count("private.example") == 1


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_redirect_to_same_hostname_is_resolved_again_and_private_answer_rejected(network, monkeypatch, transport):
    network.responses.append(_wire_response(status=302, headers={"Location": "/next"}))
    resolver = socket.getaddrinfo
    count = 0
    def rebind(host, port, *args, **kwargs):
        nonlocal count
        if host == "public.example":
            count += 1
            network.answers[host] = ["93.184.216.34" if count == 1 else "169.254.169.254"]
        return resolver(host, port, *args, **kwargs)
    monkeypatch.setattr(socket, "getaddrinfo", rebind)
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    with pytest.raises(safe_http.UnsafeUrlError, match="non-public"):
        get("https://public.example/start")
    assert count == 2
    assert len(network.connections) == 1


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_public_redirect_preserves_host_and_strips_cross_origin_secrets(network, transport):
    network.responses.append(_wire_response(status=302, headers={"Location": "https://other.example:8443/final"}))
    headers = {"Authorization": "fixture-token", "Cookie": "fixture-cookie", "Host": "wrong.example", "User-Agent": "fixture-agent"}
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    result = get("https://public.example/start", headers=headers)
    assert result.content == b"done" if transport == "requests" else result == b"done"
    assert network.connections == [("93.184.216.34", 443), ("93.184.216.34", 8443)]
    assert b"Host: other.example:8443\r\n" in network.requests[1]
    assert b"fixture-token" not in network.requests[1]
    assert b"fixture-cookie" not in network.requests[1]
    assert b"fixture-agent" in network.requests[1]
    assert network.tls_calls[1]["server_hostname"] == "other.example"


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_proxy_environment_cannot_route_the_request(network, monkeypatch, transport):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, "http://127.0.0.1:9999")
    monkeypatch.setenv("NO_PROXY", "")
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    get("https://public.example/path")
    assert network.connections == [("93.184.216.34", 443)]
    assert all(host != "127.0.0.1" for host in network.dns_calls)


def test_requests_rejects_explicit_proxy_and_insecure_tls(network):
    for kwargs in ({"proxies": {"https": "http://127.0.0.1:9999"}}, {"verify": False}):
        with pytest.raises(safe_http.UnsafeUrlError):
            safe_http.safe_get("https://public.example/path", **kwargs)
    assert network.connections == []


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_url_credentials_and_non_http_redirects_are_rejected(network, transport):
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    with pytest.raises(safe_http.UnsafeUrlError, match="credentials"):
        get("https://user:password@public.example/path")
    assert network.connections == []
    network.responses.append(_wire_response(status=302, headers={"Location": "file:///etc/passwd"}))
    with pytest.raises((safe_http.UnsafeUrlError, requests.exceptions.InvalidSchema)):
        get("https://public.example/path")
    assert len(network.connections) == 1


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_fallback_uses_only_original_validated_addresses(network, transport):
    network.answers["public.example"] = ["93.184.216.34", "93.184.216.35"]
    network.fail_addresses.add("93.184.216.34")
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    get("https://public.example/path")
    assert network.connections == [("93.184.216.34", 443), ("93.184.216.35", 443)]
    assert network.dns_calls.count("public.example") == 1


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_redirect_limit_and_loop(network, transport):
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    network.responses.append(_wire_response(status=302, headers={"Location": "/again"}))
    with pytest.raises(requests.TooManyRedirects):
        get("https://public.example/start", max_redirects=0)
    network.responses.append(_wire_response(status=302, headers={"Location": "/start"}))
    with pytest.raises(requests.TooManyRedirects, match="loop"):
        get("https://public.example/start")
    assert len(network.connections) == 2


def test_requests_preserves_response_json_status_and_query(network):
    network.responses.append(_wire_response(b'{"ok": true}', status=201, headers={"Content-Type": "application/json"}))
    response = safe_http.safe_get("https://public.example/path", params={"q": "a b"}, cookies={})
    assert isinstance(response, requests.Response)
    assert response.status_code == 201
    assert response.json() == {"ok": True}
    assert response.url == "https://public.example/path?q=a+b"
    assert b"GET /path?q=a+b HTTP/1.1" in network.requests[0]


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_public_ipv6_has_correct_socket_and_http_host(network, transport):
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    get("http://[2606:4700:4700::1111]:8080/path")
    assert network.connections == [("2606:4700:4700::1111", 8080, 0, 0)]
    assert b"Host: [2606:4700:4700::1111]:8080\r\n" in network.requests[0]


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_https_redirect_cannot_downgrade_to_plaintext(network, transport):
    network.responses.append(_wire_response(status=302, headers={"Location": "http://public.example/insecure"}))
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    with pytest.raises(safe_http.UnsafeUrlError, match="downgrade"):
        get("https://public.example/start")
    assert len(network.connections) == 1


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_mixed_dns_answers_never_open_a_socket(network, transport):
    network.answers["public.example"] = ["93.184.216.34", "10.0.0.10"]
    get = safe_http.safe_get if transport == "requests" else safe_http.safe_urllib_get
    with pytest.raises(safe_http.UnsafeUrlError, match="non-public"):
        get("https://public.example/path")
    assert network.connections == []


@pytest.mark.parametrize("transport", ["requests", "urllib"])
def test_tls_verification_failure_is_not_retried_insecurely(network, monkeypatch, transport):
    network.answers["public.example"] = ["93.184.216.34", "93.184.216.35"]
    def invalid_certificate(*args, **kwargs):
        raise ssl.SSLCertVerificationError("fixture hostname mismatch")
    if transport == "requests":
        monkeypatch.setattr(urllib3.connection, "_ssl_wrap_socket_and_match_hostname", invalid_certificate)
        with pytest.raises(requests.exceptions.SSLError):
            safe_http.safe_get("https://public.example/path")
    else:
        monkeypatch.setattr(ssl.SSLContext, "wrap_socket", invalid_certificate)
        with pytest.raises(safe_http.urllib.error.URLError):
            safe_http.safe_urllib_get("https://public.example/path")
    assert network.connections == [("93.184.216.34", 443)]
    assert network.requests == []


def test_requests_never_reads_netrc_or_environment_ca_override(network, monkeypatch):
    def no_netrc(*args, **kwargs):
        pytest.fail("outbound requests must not read .netrc credentials")
    monkeypatch.setattr(requests.sessions, "get_netrc_auth", no_netrc)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/fixture/nonexistent-ca-file")
    response = safe_http.safe_get("https://public.example/path")
    assert response.status_code == 200
    assert network.tls_calls[0]["ca_certs"] != "/fixture/nonexistent-ca-file"
