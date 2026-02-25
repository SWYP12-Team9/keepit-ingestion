"""
SSRF(Server-Side Request Forgery) 차단 로직 단위 테스트

validate_url_safety() 함수가 사설 IP, 루프백, 비표준 포트,
환경변수 기반 Allowlist/Blocklist를 올바르게 처리하는지 검증합니다.

실행:
    python -m pytest test/test_ssrf.py -v
    python -m unittest test.test_ssrf -v
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.utils.scrape_utils import validate_url_safety


# socket.gethostbyname 의 올바른 patch 경로
SOCKET_PATCH = "app.scrapers.utils.scrape_utils.socket.gethostbyname"


class TestSSRFLoopbackBlocking(unittest.TestCase):
    """루프백(loopback) 주소 차단 테스트"""

    def test_ipv4_loopback_blocked(self):
        self.assertFalse(validate_url_safety("http://127.0.0.1"))

    def test_ipv4_loopback_full_octet_blocked(self):
        self.assertFalse(validate_url_safety("http://127.0.0.2"))

    def test_localhost_domain_blocked(self):
        with patch(SOCKET_PATCH, return_value="127.0.0.1"):
            self.assertFalse(validate_url_safety("http://localhost"))

    def test_localhost_http_standard_port_blocked(self):
        # 포트 80은 표준 포트이므로 포트 검사는 통과하지만 루프백으로 차단되어야 함
        with patch(SOCKET_PATCH, return_value="127.0.0.1"):
            self.assertFalse(validate_url_safety("http://localhost:80"))


class TestSSRFPrivateIPBlocking(unittest.TestCase):
    """RFC 1918 사설 IP 대역 차단 테스트"""

    def test_class_a_private_blocked(self):
        self.assertFalse(validate_url_safety("http://10.0.0.1"))

    def test_class_a_private_upper_blocked(self):
        self.assertFalse(validate_url_safety("http://10.255.255.255"))

    def test_class_b_private_blocked(self):
        self.assertFalse(validate_url_safety("http://172.16.0.1"))

    def test_class_b_private_upper_blocked(self):
        self.assertFalse(validate_url_safety("http://172.31.255.255"))

    def test_class_c_private_blocked(self):
        self.assertFalse(validate_url_safety("http://192.168.0.1"))

    def test_class_c_private_upper_blocked(self):
        self.assertFalse(validate_url_safety("http://192.168.255.255"))

    def test_link_local_blocked(self):
        # 169.254.x.x (APIPA) 도 사설로 간주
        self.assertFalse(validate_url_safety("http://169.254.0.1"))


class TestSSRFPortBlocking(unittest.TestCase):
    """비표준 포트 차단 테스트 (80, 443 이외)"""

    def test_non_standard_port_8080_blocked(self):
        self.assertFalse(validate_url_safety("http://1.1.1.1:8080"))

    def test_non_standard_port_22_blocked(self):
        self.assertFalse(validate_url_safety("http://1.1.1.1:22"))

    def test_non_standard_port_3306_blocked(self):
        self.assertFalse(validate_url_safety("http://1.1.1.1:3306"))

    def test_non_standard_port_8000_blocked(self):
        self.assertFalse(validate_url_safety("http://1.1.1.1:8000"))

    def test_localhost_non_standard_port_blocked(self):
        # 포트 검사가 allowlist 보다 먼저 실행되므로 무조건 차단
        self.assertFalse(validate_url_safety("http://localhost:8000"))

    def test_standard_port_80_passes_port_check(self):
        # 포트 80은 통과, 이후 IP가 사설이면 차단
        self.assertFalse(validate_url_safety("http://192.168.0.1:80"))

    def test_standard_port_443_passes_port_check(self):
        # 포트 443은 통과, 이후 IP가 사설이면 차단
        self.assertFalse(validate_url_safety("https://192.168.0.1:443"))


class TestSSRFPublicURLAllowed(unittest.TestCase):
    """공개 IP/도메인은 허용되어야 함"""

    def test_cloudflare_dns_ip_allowed(self):
        # 1.1.1.1은 공개 IP, 포트 없음
        self.assertTrue(validate_url_safety("https://1.1.1.1"))

    def test_google_dns_ip_allowed(self):
        self.assertTrue(validate_url_safety("https://8.8.8.8"))

    def test_public_domain_allowed(self):
        with patch(SOCKET_PATCH, return_value="142.250.74.46"):
            self.assertTrue(validate_url_safety("https://google.com"))

    def test_public_domain_with_www_allowed(self):
        with patch(SOCKET_PATCH, return_value="142.250.74.46"):
            self.assertTrue(validate_url_safety("https://www.google.com"))

    def test_public_domain_https_allowed(self):
        with patch(SOCKET_PATCH, return_value="151.101.65.140"):
            self.assertTrue(validate_url_safety("https://youtube.com"))

    def test_public_domain_standard_port_allowed(self):
        with patch(SOCKET_PATCH, return_value="142.250.74.46"):
            self.assertTrue(validate_url_safety("https://example.com:443"))


class TestSSRFMalformedURL(unittest.TestCase):
    """잘못된 URL 형식 차단 테스트"""

    def test_empty_string_blocked(self):
        self.assertFalse(validate_url_safety(""))

    def test_no_hostname_blocked(self):
        self.assertFalse(validate_url_safety("file:///etc/passwd"))

    def test_no_scheme_no_hostname_blocked(self):
        self.assertFalse(validate_url_safety("not-a-url"))

    def test_dns_resolution_failure_blocked(self):
        # 존재하지 않는 도메인 → gaierror → False
        import socket
        with patch(SOCKET_PATCH, side_effect=socket.gaierror("Name not resolved")):
            self.assertFalse(validate_url_safety("https://nonexistent.invalid.domain"))


class TestSSRFAllowlist(unittest.TestCase):
    """SSRF_ALLOWLIST 환경변수 테스트"""

    def setUp(self):
        # 각 테스트 전 환경변수 초기화
        os.environ.pop("SSRF_ALLOWLIST", None)
        os.environ.pop("URL_BLOCKLIST", None)

    def tearDown(self):
        os.environ.pop("SSRF_ALLOWLIST", None)
        os.environ.pop("URL_BLOCKLIST", None)

    def test_allowlist_localhost_permits_loopback(self):
        os.environ["SSRF_ALLOWLIST"] = "localhost"
        with patch(SOCKET_PATCH, return_value="127.0.0.1"):
            self.assertTrue(validate_url_safety("http://localhost"))

    def test_allowlist_ip_permits_private_ip(self):
        os.environ["SSRF_ALLOWLIST"] = "192.168.0.1"
        self.assertTrue(validate_url_safety("http://192.168.0.1"))

    def test_allowlist_does_not_permit_other_private_ip(self):
        # 192.168.0.1만 허용했으므로 10.0.0.1은 여전히 차단
        os.environ["SSRF_ALLOWLIST"] = "192.168.0.1"
        self.assertFalse(validate_url_safety("http://10.0.0.1"))

    def test_allowlist_multiple_hosts(self):
        os.environ["SSRF_ALLOWLIST"] = "localhost, 127.0.0.1"
        self.assertTrue(validate_url_safety("http://127.0.0.1"))

    def test_allowlist_does_not_bypass_port_check(self):
        # 포트 검사가 allowlist보다 먼저 실행됨
        os.environ["SSRF_ALLOWLIST"] = "localhost"
        self.assertFalse(validate_url_safety("http://localhost:8000"))

    def test_no_allowlist_private_ip_blocked(self):
        # allowlist 없을 때 기본 동작 확인
        self.assertFalse(validate_url_safety("http://192.168.0.1"))


class TestSSRFBlocklist(unittest.TestCase):
    """URL_BLOCKLIST 환경변수 테스트"""

    def setUp(self):
        os.environ.pop("SSRF_ALLOWLIST", None)
        os.environ.pop("URL_BLOCKLIST", None)

    def tearDown(self):
        os.environ.pop("SSRF_ALLOWLIST", None)
        os.environ.pop("URL_BLOCKLIST", None)

    def test_blocklist_exact_domain_blocked(self):
        os.environ["URL_BLOCKLIST"] = "evil.com"
        with patch(SOCKET_PATCH, return_value="1.2.3.4"):
            self.assertFalse(validate_url_safety("https://evil.com"))

    def test_blocklist_wildcard_subdomain_blocked(self):
        os.environ["URL_BLOCKLIST"] = "*.evil.com"
        with patch(SOCKET_PATCH, return_value="1.2.3.4"):
            self.assertFalse(validate_url_safety("https://sub.evil.com"))

    def test_blocklist_wildcard_root_domain_also_blocked(self):
        # *.evil.com 패턴에서 evil.com 자체도 hostname == domain_part 로 차단
        os.environ["URL_BLOCKLIST"] = "*.evil.com"
        with patch(SOCKET_PATCH, return_value="1.2.3.4"):
            self.assertFalse(validate_url_safety("https://evil.com"))

    def test_blocklist_does_not_block_other_domains(self):
        os.environ["URL_BLOCKLIST"] = "evil.com"
        with patch(SOCKET_PATCH, return_value="142.250.74.46"):
            self.assertTrue(validate_url_safety("https://good.com"))

    def test_blocklist_multiple_entries(self):
        os.environ["URL_BLOCKLIST"] = "evil.com, bad.net"
        with patch(SOCKET_PATCH, return_value="1.2.3.4"):
            self.assertFalse(validate_url_safety("https://evil.com"))
            self.assertFalse(validate_url_safety("https://bad.net"))

    def test_blocklist_wildcard_deep_subdomain_blocked(self):
        os.environ["URL_BLOCKLIST"] = "*.evil.com"
        with patch(SOCKET_PATCH, return_value="1.2.3.4"):
            self.assertFalse(validate_url_safety("https://deep.sub.evil.com"))


if __name__ == "__main__":
    unittest.main()
