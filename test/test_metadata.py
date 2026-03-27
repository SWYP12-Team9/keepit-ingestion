"""
기본 메타데이터 생성(generate_basic_metadata) 단위 테스트
"""

import pytest

from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.utils.scrape_utils import generate_basic_metadata


EXPECTED_API_KEYS = {
    "success",
    "title",
    "description",
    "thumbnail_url",
    "favicon_url",
    "site_name",
    "url",
    "content",
}


@pytest.fixture
def example_result():
    return generate_basic_metadata("https://www.example.com/some/path")


def test_generate_basic_metadata_returns_scrape_response(example_result):
    assert isinstance(example_result, ScrapeResponse)


def test_generate_basic_metadata_success_is_true(example_result):
    assert example_result.success is True


def test_generate_basic_metadata_description_is_empty(example_result):
    assert example_result.description == ""


def test_generate_basic_metadata_content_is_empty(example_result):
    assert example_result.content == ""


def test_generate_basic_metadata_thumbnail_is_none(example_result):
    assert example_result.thumbnail_url is None


def test_generate_basic_metadata_keeps_input_url(example_result):
    assert example_result.url == "https://www.example.com/some/path"


def test_generate_basic_metadata_to_dict_shape(example_result):
    assert set(example_result.to_dict().keys()) == EXPECTED_API_KEYS


@pytest.mark.parametrize(
    ("url", "expected_title"),
    [
        ("https://www.google.com/search?q=test", "google.com"),
        ("https://www.google.com/", "google.com"),
        ("https://youtube.com/watch?v=abc", "youtube.com"),
        ("https://blog.naver.com/user/123", "blog.naver.com"),
        ("https://www.naver.co.kr/", "naver.co.kr"),
        ("https://www.coupang.com/vp/products/1", "coupang.com"),
        ("https://velog.io/@user/post", "velog.io"),
        ("https://myblog.tistory.com/entry/1", "myblog.tistory.com"),
    ],
)
def test_generate_basic_metadata_domain_mapping(url, expected_title):
    result = generate_basic_metadata(url)
    assert result.title == expected_title
    assert result.site_name == expected_title


@pytest.mark.parametrize(
    ("url", "expected_prefix"),
    [
        ("https://example.com/path", "https://"),
        ("http://example.com/path", "http://"),
    ],
)
def test_generate_basic_metadata_favicon_scheme(url, expected_prefix):
    result = generate_basic_metadata(url)
    assert result.favicon_url.startswith(expected_prefix)


def test_generate_basic_metadata_favicon_suffix():
    result = generate_basic_metadata("https://example.com/page")
    assert result.favicon_url.endswith("/favicon.ico")


def test_generate_basic_metadata_favicon_contains_netloc():
    result = generate_basic_metadata("https://www.youtube.com/watch?v=abc")
    assert "www.youtube.com" in result.favicon_url


def test_generate_basic_metadata_favicon_exact_blog_naver():
    result = generate_basic_metadata("https://blog.naver.com/user/123")
    assert result.favicon_url == "https://blog.naver.com/favicon.ico"


def test_generate_basic_metadata_none_url_fallback():
    result = generate_basic_metadata(None)
    assert result.success is True
    assert result.title == "Website"
    assert result.site_name == "Website"
    assert result.favicon_url is None
    assert result.description == ""
    assert result.content == ""
    assert result.thumbnail_url is None


def test_generate_basic_metadata_none_url_to_dict_shape():
    result = generate_basic_metadata(None)
    assert set(result.to_dict().keys()) == EXPECTED_API_KEYS
