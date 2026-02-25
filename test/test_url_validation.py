"""
URL 유효성 검사 및 사이트 타입 감지 단위 테스트

normalize_url(), is_*_url(), detect_site_type() 함수의 동작을 검증합니다.

실행:
    python -m pytest test/test_url_validation.py -v
    python -m unittest test.test_url_validation -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.utils.scrape_utils import (
    normalize_url,
    is_youtube_url,
    is_instagram_url,
    is_naver_blog_url,
    is_velog_url,
    is_tistory_url,
    is_google_search_url,
    is_coupang_url,
    is_naver_map_url,
    is_naver_search_url,
    is_daum_search_url,
    detect_site_type,
)


class TestNormalizeURL(unittest.TestCase):
    """normalize_url() - 스킴 없는 URL에 https:// 추가"""

    def test_no_scheme_adds_https(self):
        self.assertEqual(normalize_url("example.com"), "https://example.com")

    def test_no_scheme_with_path_adds_https(self):
        self.assertEqual(normalize_url("example.com/path"), "https://example.com/path")

    def test_http_scheme_unchanged(self):
        self.assertEqual(normalize_url("http://example.com"), "http://example.com")

    def test_https_scheme_unchanged(self):
        self.assertEqual(normalize_url("https://example.com"), "https://example.com")

    def test_empty_string_returns_empty(self):
        self.assertEqual(normalize_url(""), "")

    def test_none_returns_none(self):
        self.assertIsNone(normalize_url(None))

    def test_www_no_scheme_adds_https(self):
        self.assertEqual(normalize_url("www.youtube.com"), "https://www.youtube.com")


class TestIsYoutubeURL(unittest.TestCase):
    """is_youtube_url() - 다양한 YouTube URL 변형 인식"""

    def test_www_youtube_watch(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=abc123"))

    def test_youtube_no_www(self):
        self.assertTrue(is_youtube_url("https://youtube.com/watch?v=abc123"))

    def test_mobile_youtube(self):
        self.assertTrue(is_youtube_url("https://m.youtube.com/watch?v=abc123"))

    def test_youtu_be_short_link(self):
        self.assertTrue(is_youtube_url("https://youtu.be/abc123"))

    def test_youtube_shorts(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/shorts/abc123"))

    def test_youtube_playlist(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/playlist?list=PLabc"))

    def test_youtube_channel(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/@channelname"))

    def test_non_youtube_google_false(self):
        self.assertFalse(is_youtube_url("https://google.com"))

    def test_non_youtube_vimeo_false(self):
        self.assertFalse(is_youtube_url("https://vimeo.com/12345"))

    def test_empty_string_false(self):
        self.assertFalse(is_youtube_url(""))


class TestIsInstagramURL(unittest.TestCase):
    """is_instagram_url() - Instagram URL 인식"""

    def test_instagram_post(self):
        self.assertTrue(is_instagram_url("https://www.instagram.com/p/abc123/"))

    def test_instagram_profile(self):
        self.assertTrue(is_instagram_url("https://instagram.com/username"))

    def test_instagram_reel(self):
        self.assertTrue(is_instagram_url("https://www.instagram.com/reel/abc123/"))

    def test_non_instagram_false(self):
        self.assertFalse(is_instagram_url("https://facebook.com"))

    def test_non_instagram_twitter_false(self):
        self.assertFalse(is_instagram_url("https://twitter.com"))


class TestIsNaverBlogURL(unittest.TestCase):
    """is_naver_blog_url() - 네이버 블로그 URL 인식"""

    def test_naver_blog_post(self):
        self.assertTrue(is_naver_blog_url("https://blog.naver.com/user/123456"))

    def test_naver_blog_root(self):
        self.assertTrue(is_naver_blog_url("https://blog.naver.com/"))

    def test_naver_main_false(self):
        self.assertFalse(is_naver_blog_url("https://www.naver.com"))

    def test_naver_news_false(self):
        self.assertFalse(is_naver_blog_url("https://n.news.naver.com/article/123"))


class TestIsVelogURL(unittest.TestCase):
    """is_velog_url() - Velog URL 인식"""

    def test_velog_post(self):
        self.assertTrue(is_velog_url("https://velog.io/@username/post-title"))

    def test_velog_profile(self):
        self.assertTrue(is_velog_url("https://velog.io/@username"))

    def test_velog_root(self):
        self.assertTrue(is_velog_url("https://velog.io"))

    def test_non_velog_false(self):
        self.assertFalse(is_velog_url("https://medium.com/@user/post"))


class TestIsTistoryURL(unittest.TestCase):
    """is_tistory_url() - 티스토리 URL 인식"""

    def test_tistory_post(self):
        self.assertTrue(is_tistory_url("https://myblog.tistory.com/entry/title"))

    def test_tistory_main(self):
        self.assertTrue(is_tistory_url("https://www.tistory.com"))

    def test_non_tistory_false(self):
        self.assertFalse(is_tistory_url("https://brunch.co.kr"))


class TestIsGoogleSearchURL(unittest.TestCase):
    """is_google_search_url() - Google 검색/메인 URL 인식"""

    def test_google_search(self):
        self.assertTrue(is_google_search_url("https://www.google.com/search?q=test"))

    def test_google_main(self):
        self.assertTrue(is_google_search_url("https://google.com"))

    def test_google_co_kr(self):
        self.assertTrue(is_google_search_url("https://www.google.co.kr/search?q=test"))

    def test_non_google_false(self):
        self.assertFalse(is_google_search_url("https://bing.com/search?q=test"))


class TestIsCoupangURL(unittest.TestCase):
    """is_coupang_url() - 쿠팡 URL 인식"""

    def test_coupang_product(self):
        self.assertTrue(is_coupang_url("https://www.coupang.com/vp/products/12345"))

    def test_coupang_main(self):
        self.assertTrue(is_coupang_url("https://coupang.com"))

    def test_non_coupang_false(self):
        self.assertFalse(is_coupang_url("https://gmarket.co.kr"))


class TestIsNaverMapURL(unittest.TestCase):
    """is_naver_map_url() - 네이버 지도 URL 인식"""

    def test_naver_map_place(self):
        self.assertTrue(is_naver_map_url("https://map.naver.com/v5/entry/place/123"))

    def test_naver_me_short_url(self):
        self.assertTrue(is_naver_map_url("https://naver.me/abc123"))

    def test_non_map_false(self):
        self.assertFalse(is_naver_map_url("https://kakaomap.com"))


class TestIsNaverSearchURL(unittest.TestCase):
    """is_naver_search_url() - 네이버 검색 URL 인식"""

    def test_naver_search(self):
        self.assertTrue(is_naver_search_url("https://search.naver.com/search.naver?query=test"))

    def test_non_naver_search_false(self):
        self.assertFalse(is_naver_search_url("https://www.naver.com"))


class TestIsDaumSearchURL(unittest.TestCase):
    """is_daum_search_url() - Daum 검색 URL 인식"""

    def test_daum_search(self):
        self.assertTrue(is_daum_search_url("https://search.daum.net/search?q=test"))

    def test_non_daum_search_false(self):
        self.assertFalse(is_daum_search_url("https://www.daum.net"))


class TestDetectSiteType(unittest.TestCase):
    """detect_site_type() - 사이트 타입 분류 통합 테스트"""

    def test_youtube_type(self):
        self.assertEqual(detect_site_type("https://www.youtube.com/watch?v=abc"), "youtube")

    def test_youtu_be_type(self):
        self.assertEqual(detect_site_type("https://youtu.be/abc"), "youtube")

    def test_instagram_type(self):
        self.assertEqual(detect_site_type("https://www.instagram.com/p/abc/"), "instagram")

    def test_naver_blog_type(self):
        self.assertEqual(detect_site_type("https://blog.naver.com/user/123"), "naver_blog")

    def test_velog_type(self):
        self.assertEqual(detect_site_type("https://velog.io/@user/post"), "velog")

    def test_tistory_type(self):
        self.assertEqual(detect_site_type("https://blog.tistory.com/entry/1"), "tistory")

    def test_google_search_type(self):
        self.assertEqual(detect_site_type("https://www.google.com/search?q=hi"), "google_search")

    def test_naver_search_type(self):
        self.assertEqual(detect_site_type("https://search.naver.com/search.naver?query=hi"), "naver_search")

    def test_daum_search_type(self):
        self.assertEqual(detect_site_type("https://search.daum.net/search?q=hi"), "daum_search")

    def test_naver_map_type(self):
        self.assertEqual(detect_site_type("https://map.naver.com/v5/entry/place/123"), "naver_map")

    def test_coupang_type(self):
        self.assertEqual(detect_site_type("https://www.coupang.com/vp/products/1"), "coupang")

    def test_generic_type(self):
        self.assertEqual(detect_site_type("https://example.com/article"), "generic")

    def test_unknown_domain_generic(self):
        self.assertEqual(detect_site_type("https://brunch.co.kr/@user/post"), "generic")


if __name__ == "__main__":
    unittest.main()
