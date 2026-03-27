"""
URL 유효성 검사 및 사이트 타입 감지 단위 테스트
"""

import pytest

from app.scrapers.utils.scrape_utils import (
    detect_site_type,
    is_coupang_url,
    is_daum_search_url,
    is_google_search_url,
    is_instagram_url,
    is_naver_blog_url,
    is_naver_map_url,
    is_naver_search_url,
    is_tistory_url,
    is_velog_url,
    is_youtube_url,
    normalize_url,
)


@pytest.mark.parametrize(
    ("raw_url", "expected"),
    [
        ("example.com", "https://example.com"),
        ("example.com/path", "https://example.com/path"),
        ("http://example.com", "http://example.com"),
        ("https://example.com", "https://example.com"),
        ("", ""),
        (None, None),
        ("www.youtube.com", "https://www.youtube.com"),
    ],
)
def test_normalize_url(raw_url, expected):
    assert normalize_url(raw_url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc123", True),
        ("https://youtube.com/watch?v=abc123", True),
        ("https://m.youtube.com/watch?v=abc123", True),
        ("https://youtu.be/abc123", True),
        ("https://www.youtube.com/shorts/abc123", True),
        ("https://www.youtube.com/playlist?list=PLabc", True),
        ("https://www.youtube.com/@channelname", True),
        ("https://google.com", False),
        ("https://vimeo.com/12345", False),
        ("", False),
    ],
)
def test_is_youtube_url(url, expected):
    assert is_youtube_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.instagram.com/p/abc123/", True),
        ("https://instagram.com/username", True),
        ("https://www.instagram.com/reel/abc123/", True),
        ("https://facebook.com", False),
        ("https://twitter.com", False),
    ],
)
def test_is_instagram_url(url, expected):
    assert is_instagram_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://blog.naver.com/user/123456", True),
        ("https://blog.naver.com/", True),
        ("https://www.naver.com", False),
        ("https://n.news.naver.com/article/123", False),
    ],
)
def test_is_naver_blog_url(url, expected):
    assert is_naver_blog_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://velog.io/@username/post-title", True),
        ("https://velog.io/@username", True),
        ("https://velog.io", True),
        ("https://medium.com/@user/post", False),
    ],
)
def test_is_velog_url(url, expected):
    assert is_velog_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://myblog.tistory.com/entry/title", True),
        ("https://www.tistory.com", True),
        ("https://brunch.co.kr", False),
    ],
)
def test_is_tistory_url(url, expected):
    assert is_tistory_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.google.com/search?q=test", True),
        ("https://google.com", True),
        ("https://www.google.co.kr/search?q=test", True),
        ("https://bing.com/search?q=test", False),
    ],
)
def test_is_google_search_url(url, expected):
    assert is_google_search_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.coupang.com/vp/products/12345", True),
        ("https://coupang.com", True),
        ("https://gmarket.co.kr", False),
    ],
)
def test_is_coupang_url(url, expected):
    assert is_coupang_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://map.naver.com/v5/entry/place/123", True),
        ("https://naver.me/abc123", True),
        ("https://kakaomap.com", False),
    ],
)
def test_is_naver_map_url(url, expected):
    assert is_naver_map_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://search.naver.com/search.naver?query=test", True),
        ("https://www.naver.com", False),
    ],
)
def test_is_naver_search_url(url, expected):
    assert is_naver_search_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://search.daum.net/search?q=test", True),
        ("https://www.daum.net", False),
    ],
)
def test_is_daum_search_url(url, expected):
    assert is_daum_search_url(url) is expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube"),
        ("https://youtu.be/abc", "youtube"),
        ("https://www.instagram.com/p/abc/", "instagram"),
        ("https://blog.naver.com/user/123", "naver_blog"),
        ("https://velog.io/@user/post", "velog"),
        ("https://blog.tistory.com/entry/1", "tistory"),
        ("https://www.google.com/search?q=hi", "google_search"),
        ("https://search.naver.com/search.naver?query=hi", "naver_search"),
        ("https://search.daum.net/search?q=hi", "daum_search"),
        ("https://map.naver.com/v5/entry/place/123", "naver_map"),
        ("https://www.coupang.com/vp/products/1", "coupang"),
        ("https://example.com/article", "generic"),
        ("https://brunch.co.kr/@user/post", "generic"),
    ],
)
def test_detect_site_type(url, expected):
    assert detect_site_type(url) == expected
