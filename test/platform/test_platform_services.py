"""
플랫폼 서비스 테스트
"""

import pytest

from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.service.platform.coupang_service import scrape_coupang
from app.scrapers.service.platform.daum_service import scrape_daum_search
from app.scrapers.service.platform.google_service import scrape_google_search
from app.scrapers.service.platform.naver_service import scrape_naver_search
from app.scrapers.service.platform.youtube_service import (
    extract_video_id,
    normalize_youtube_url,
    scrape_youtube,
)


def test_extract_video_id_standard():
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_short():
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"


def test_extract_video_id_invalid():
    assert extract_video_id("https://www.google.com") is None


def test_normalize_youtube_url():
    url = normalize_youtube_url(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
    )
    assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_normalize_invalid_youtube_url():
    assert normalize_youtube_url("https://www.google.com") is None


@pytest.mark.asyncio
async def test_scrape_youtube_returns_scrape_response():
    result = await scrape_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert result.site_name == "YouTube"
    assert result.url is not None


def test_scrape_google_search_with_query():
    result = scrape_google_search("https://www.google.com/search?q=python")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert "python" in result.title
    assert result.site_name == "Google"


def test_scrape_google_search_without_query():
    result = scrape_google_search("https://www.google.com/")
    assert isinstance(result, ScrapeResponse)
    assert result.title == "Google"


def test_scrape_naver_search_with_query():
    result = scrape_naver_search("https://search.naver.com/search.naver?query=파이썬")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert "파이썬" in result.title
    assert result.site_name == "Naver"


def test_scrape_naver_search_without_query():
    result = scrape_naver_search("https://search.naver.com/search.naver")
    assert isinstance(result, ScrapeResponse)
    assert result.title == "네이버 검색"


def test_scrape_daum_search_with_query():
    result = scrape_daum_search("https://search.daum.net/search?q=강남+맛집")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert "강남 맛집" in result.title
    assert result.site_name == "Daum"


def test_scrape_daum_search_without_query():
    result = scrape_daum_search("https://search.daum.net/search")
    assert isinstance(result, ScrapeResponse)
    assert result.title == "Daum 검색"


def test_scrape_coupang_returns_scrape_response():
    result = scrape_coupang("https://www.coupang.com/vp/products/12345")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert "coupang.com" in (result.site_name or "")
