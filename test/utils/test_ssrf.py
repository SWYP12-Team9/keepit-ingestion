"""
SSRF(Server-Side Request Forgery) 차단 로직 단위 테스트
"""

import socket

import pytest

from app.scrapers.utils.scrape_utils import validate_url_safety


SOCKET_PATCH = "app.scrapers.utils.scrape_utils.socket.gethostbyname"


@pytest.fixture(autouse=True)
def clear_ssrf_env(monkeypatch):
    monkeypatch.delenv("SSRF_ALLOWLIST", raising=False)
    monkeypatch.delenv("URL_BLOCKLIST", raising=False)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://127.0.0.2",
    ],
)
def test_loopback_ipv4_is_blocked(url):
    assert validate_url_safety(url) is False


def test_localhost_domain_is_blocked(monkeypatch):
    monkeypatch.setattr(SOCKET_PATCH, lambda hostname: "127.0.0.1")
    assert validate_url_safety("http://localhost") is False


def test_localhost_standard_port_is_blocked(monkeypatch):
    monkeypatch.setattr(SOCKET_PATCH, lambda hostname: "127.0.0.1")
    assert validate_url_safety("http://localhost:80") is False


@pytest.mark.parametrize(
    "url",
    [
        "http://10.0.0.1",
        "http://10.255.255.255",
        "http://172.16.0.1",
        "http://172.31.255.255",
        "http://192.168.0.1",
        "http://192.168.255.255",
        "http://169.254.0.1",
    ],
)
def test_private_and_link_local_ips_are_blocked(url):
    assert validate_url_safety(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "http://1.1.1.1:8080",
        "http://1.1.1.1:22",
        "http://1.1.1.1:3306",
        "http://1.1.1.1:8000",
        "http://localhost:8000",
    ],
)
def test_non_standard_ports_are_blocked(url):
    assert validate_url_safety(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "http://192.168.0.1:80",
        "https://192.168.0.1:443",
    ],
)
def test_standard_ports_still_block_private_ips(url):
    assert validate_url_safety(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://1.1.1.1",
        "https://8.8.8.8",
    ],
)
def test_public_ip_urls_are_allowed(url):
    assert validate_url_safety(url) is True


@pytest.mark.parametrize(
    ("url", "resolved_ip"),
    [
        ("https://google.com", "142.250.74.46"),
        ("https://www.google.com", "142.250.74.46"),
        ("https://youtube.com", "151.101.65.140"),
        ("https://example.com:443", "142.250.74.46"),
    ],
)
def test_public_domains_are_allowed(monkeypatch, url, resolved_ip):
    monkeypatch.setattr(SOCKET_PATCH, lambda hostname: resolved_ip)
    assert validate_url_safety(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "file:///etc/passwd",
        "not-a-url",
    ],
)
def test_malformed_urls_are_blocked(url):
    assert validate_url_safety(url) is False


def test_dns_resolution_failure_is_blocked(monkeypatch):
    def raise_gaierror(hostname):
        raise socket.gaierror("Name not resolved")

    monkeypatch.setattr(SOCKET_PATCH, raise_gaierror)
    assert validate_url_safety("https://nonexistent.invalid.domain") is False


def test_allowlist_allows_localhost(monkeypatch):
    monkeypatch.setenv("SSRF_ALLOWLIST", "localhost")
    monkeypatch.setattr(SOCKET_PATCH, lambda hostname: "127.0.0.1")
    assert validate_url_safety("http://localhost") is True


def test_allowlist_allows_private_ip(monkeypatch):
    monkeypatch.setenv("SSRF_ALLOWLIST", "192.168.0.1")
    assert validate_url_safety("http://192.168.0.1") is True


def test_allowlist_does_not_allow_other_private_ip(monkeypatch):
    monkeypatch.setenv("SSRF_ALLOWLIST", "192.168.0.1")
    assert validate_url_safety("http://10.0.0.1") is False


def test_allowlist_multiple_hosts(monkeypatch):
    monkeypatch.setenv("SSRF_ALLOWLIST", "localhost, 127.0.0.1")
    assert validate_url_safety("http://127.0.0.1") is True


def test_allowlist_does_not_bypass_port_check(monkeypatch):
    monkeypatch.setenv("SSRF_ALLOWLIST", "localhost")
    assert validate_url_safety("http://localhost:8000") is False


def test_no_allowlist_private_ip_still_blocked():
    assert validate_url_safety("http://192.168.0.1") is False


@pytest.mark.parametrize(
    ("blocklist", "url"),
    [
        ("evil.com", "https://evil.com"),
        ("*.evil.com", "https://sub.evil.com"),
        ("*.evil.com", "https://evil.com"),
        ("*.evil.com", "https://deep.sub.evil.com"),
    ],
)
def test_blocklist_blocks_matching_domains(monkeypatch, blocklist, url):
    monkeypatch.setenv("URL_BLOCKLIST", blocklist)
    monkeypatch.setattr(SOCKET_PATCH, lambda hostname: "1.2.3.4")
    assert validate_url_safety(url) is False


def test_blocklist_does_not_block_other_domains(monkeypatch):
    monkeypatch.setenv("URL_BLOCKLIST", "evil.com")
    monkeypatch.setattr(SOCKET_PATCH, lambda hostname: "142.250.74.46")
    assert validate_url_safety("https://good.com") is True


def test_blocklist_multiple_entries(monkeypatch):
    monkeypatch.setenv("URL_BLOCKLIST", "evil.com, bad.net")
    monkeypatch.setattr(SOCKET_PATCH, lambda hostname: "1.2.3.4")
    assert validate_url_safety("https://evil.com") is False
    assert validate_url_safety("https://bad.net") is False
