"""
기본 메타데이터 생성(generate_basic_metadata) 단위 테스트

스크래핑 실패/차단 시 URL에서 최소한의 메타데이터를 만들어내는
generate_basic_metadata() 함수의 반환값 구조 및 내용을 검증합니다.

실행:
    python -m pytest test/test_metadata.py -v
    python -m unittest test.test_metadata -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.utils.scrape_utils import generate_basic_metadata


REQUIRED_KEYS = {"success", "title", "description", "thumbnail_url", "favicon_url", "site_name", "url", "content"}


class TestGenerateBasicMetadataStructure(unittest.TestCase):
    """반환 딕셔너리의 키 구조 검증"""

    def setUp(self):
        self.url = "https://www.example.com/some/path"
        self.result = generate_basic_metadata(self.url)

    def test_returns_dict(self):
        self.assertIsInstance(self.result, dict)

    def test_all_required_keys_present(self):
        self.assertEqual(REQUIRED_KEYS, set(self.result.keys()))

    def test_success_is_true(self):
        self.assertTrue(self.result["success"])

    def test_description_is_empty_string(self):
        self.assertEqual(self.result["description"], "")

    def test_content_is_empty_string(self):
        self.assertEqual(self.result["content"], "")

    def test_thumbnail_url_is_none(self):
        self.assertIsNone(self.result["thumbnail_url"])

    def test_url_matches_input(self):
        self.assertEqual(self.result["url"], self.url)


class TestGenerateBasicMetadataDomain(unittest.TestCase):
    """도메인 추출 및 www. 제거 로직 검증"""

    def test_www_removed_from_title(self):
        result = generate_basic_metadata("https://www.google.com/search?q=test")
        self.assertEqual(result["title"], "google.com")

    def test_www_removed_from_site_name(self):
        result = generate_basic_metadata("https://www.google.com/")
        self.assertEqual(result["site_name"], "google.com")

    def test_no_www_domain_preserved(self):
        result = generate_basic_metadata("https://youtube.com/watch?v=abc")
        self.assertEqual(result["title"], "youtube.com")

    def test_subdomain_preserved(self):
        result = generate_basic_metadata("https://blog.naver.com/user/123")
        self.assertEqual(result["title"], "blog.naver.com")

    def test_title_equals_site_name(self):
        result = generate_basic_metadata("https://www.coupang.com/vp/products/1")
        self.assertEqual(result["title"], result["site_name"])

    def test_co_kr_domain(self):
        result = generate_basic_metadata("https://www.naver.co.kr/")
        self.assertEqual(result["title"], "naver.co.kr")


class TestGenerateBasicMetadataFavicon(unittest.TestCase):
    """favicon_url 형식 검증"""

    def test_favicon_uses_https_scheme(self):
        result = generate_basic_metadata("https://example.com/path")
        self.assertTrue(result["favicon_url"].startswith("https://"))

    def test_favicon_uses_http_scheme(self):
        result = generate_basic_metadata("http://example.com/path")
        self.assertTrue(result["favicon_url"].startswith("http://"))

    def test_favicon_ends_with_favicon_ico(self):
        result = generate_basic_metadata("https://example.com/page")
        self.assertTrue(result["favicon_url"].endswith("/favicon.ico"))

    def test_favicon_contains_netloc(self):
        result = generate_basic_metadata("https://www.youtube.com/watch?v=abc")
        self.assertIn("www.youtube.com", result["favicon_url"])

    def test_favicon_format_full(self):
        result = generate_basic_metadata("https://blog.naver.com/user/123")
        self.assertEqual(result["favicon_url"], "https://blog.naver.com/favicon.ico")


class TestGenerateBasicMetadataFallback(unittest.TestCase):
    """파싱 불가 URL / 예외 상황의 폴백 동작 검증"""

    def test_none_url_returns_fallback(self):
        result = generate_basic_metadata(None)
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], "Website")
        self.assertEqual(result["site_name"], "Website")
        self.assertIsNone(result["favicon_url"])

    def test_fallback_has_all_required_keys(self):
        result = generate_basic_metadata(None)
        self.assertEqual(REQUIRED_KEYS, set(result.keys()))

    def test_fallback_success_true(self):
        result = generate_basic_metadata(None)
        self.assertTrue(result["success"])

    def test_fallback_content_empty(self):
        result = generate_basic_metadata(None)
        self.assertEqual(result["content"], "")

    def test_fallback_description_empty(self):
        result = generate_basic_metadata(None)
        self.assertEqual(result["description"], "")

    def test_fallback_thumbnail_none(self):
        result = generate_basic_metadata(None)
        self.assertIsNone(result["thumbnail_url"])


class TestGenerateBasicMetadataVariousURLs(unittest.TestCase):
    """실제 서비스 URL에 대한 메타데이터 생성 검증"""

    def _assert_basic_structure(self, result, expected_title, input_url):
        self.assertTrue(result["success"])
        self.assertEqual(result["title"], expected_title)
        self.assertEqual(result["site_name"], expected_title)
        self.assertEqual(result["url"], input_url)
        self.assertIsNone(result["thumbnail_url"])

    def test_coupang_url(self):
        url = "https://www.coupang.com/vp/products/99999"
        result = generate_basic_metadata(url)
        self._assert_basic_structure(result, "coupang.com", url)

    def test_youtube_url(self):
        url = "https://www.youtube.com/watch?v=abc123"
        result = generate_basic_metadata(url)
        self._assert_basic_structure(result, "youtube.com", url)

    def test_velog_url(self):
        url = "https://velog.io/@user/post"
        result = generate_basic_metadata(url)
        self._assert_basic_structure(result, "velog.io", url)

    def test_tistory_url(self):
        url = "https://myblog.tistory.com/entry/1"
        result = generate_basic_metadata(url)
        self._assert_basic_structure(result, "myblog.tistory.com", url)


if __name__ == "__main__":
    unittest.main()
