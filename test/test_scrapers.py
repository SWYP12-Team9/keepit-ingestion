"""
각 스크래퍼의 ScrapeResponse 반환 및 기본 동작을 검증하는 테스트
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.service.scrape_orchestrator import scrape_url
from app.scrapers.service import scrape_orchestrator
from app.scrapers.service.platform.youtube_service import (
    scrape_youtube,
    extract_video_id,
    normalize_youtube_url,
)
from app.scrapers.service.platform.web_service import scrape_web
from app.scrapers.service.platform.google_service import scrape_google_search
from app.scrapers.service.platform.naver_service import scrape_naver_search
from app.scrapers.service.platform.daum_service import scrape_daum_search
from app.scrapers.service.platform.coupang_service import scrape_coupang
from app.scrapers.utils.scrape_utils import generate_basic_metadata


# ScrapeResponse DTO 테스트

class TestScrapeResponse:
    """ScrapeResponse DTO 기본 동작 테스트"""

    def test_create_default(self):
        result = ScrapeResponse()
        assert result.success is True
        assert result.url == ""
        assert result.title is None

    def test_create_with_values(self):
        result = ScrapeResponse(
            success=True,
            title="Test",
            description="Desc",
            url="https://example.com",
        )
        assert result.title == "Test"
        assert result.description == "Desc"
        assert result.url == "https://example.com"

    def test_to_dict_excludes_none_content(self):
        result = ScrapeResponse(success=True, title="Test", url="https://example.com")
        d = result.to_dict()
        assert "content" not in d
        assert "error" not in d

    def test_to_dict_includes_content_when_set(self):
        result = ScrapeResponse(success=True, title="Test", url="https://example.com", content="Hello")
        d = result.to_dict()
        assert d["content"] == "Hello"

    def test_attribute_mutation(self):
        result = ScrapeResponse(success=True, title="Old")
        result.title = "New"
        result.content = "Added"
        assert result.title == "New"
        assert result.content == "Added"


# generate_basic_metadata 테스트

class TestGenerateBasicMetadata:
    """generate_basic_metadata가 ScrapeResponse를 반환하는지 확인"""

    def test_returns_scrape_response(self):
        result = generate_basic_metadata("https://example.com")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True

    def test_extracts_domain_as_title(self):
        result = generate_basic_metadata("https://www.example.com/path")
        assert result.title == "example.com"
        assert result.site_name == "example.com"

    def test_invalid_url(self):
        result = generate_basic_metadata("")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True


# YouTube 스크래퍼 테스트

class TestYoutubeScraper:
    """YouTube 관련 유틸리티 및 스크래퍼 테스트"""

    def test_extract_video_id_standard(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_short(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid(self):
        assert extract_video_id("https://www.google.com") is None

    def test_normalize_youtube_url(self):
        url = normalize_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf")
        assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_normalize_invalid_url(self):
        assert normalize_youtube_url("https://www.google.com") is None

    @pytest.mark.asyncio
    async def test_scrape_youtube_returns_scrape_response(self):
        result = await scrape_youtube("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert result.site_name == "YouTube"
        assert result.url is not None


# Google 검색 스크래퍼 테스트

class TestGoogleScraper:
    """Google 검색 URL 파싱 테스트"""

    def test_with_query(self):
        result = scrape_google_search("https://www.google.com/search?q=python")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert "python" in result.title
        assert result.site_name == "Google"

    def test_without_query(self):
        result = scrape_google_search("https://www.google.com/")
        assert isinstance(result, ScrapeResponse)
        assert result.title == "Google"


# Naver 검색 스크래퍼 테스트

class TestNaverScraper:
    """Naver 검색 URL 파싱 테스트"""

    def test_with_query(self):
        result = scrape_naver_search("https://search.naver.com/search.naver?query=파이썬")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert "파이썬" in result.title
        assert result.site_name == "Naver"

    def test_without_query(self):
        result = scrape_naver_search("https://search.naver.com/search.naver")
        assert isinstance(result, ScrapeResponse)
        assert result.title == "네이버 검색"


# Daum 검색 스크래퍼 테스트

class TestDaumScraper:
    """Daum 검색 URL 파싱 테스트"""

    def test_with_query(self):
        result = scrape_daum_search("https://search.daum.net/search?q=강남+맛집")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert "강남 맛집" in result.title
        assert result.site_name == "Daum"

    def test_without_query(self):
        result = scrape_daum_search("https://search.daum.net/search")
        assert isinstance(result, ScrapeResponse)
        assert result.title == "Daum 검색"


# Coupang 스크래퍼 테스트

class TestCoupangScraper:
    """Coupang 기본 메타데이터 반환 테스트"""

    def test_returns_scrape_response(self):
        result = scrape_coupang("https://www.coupang.com/vp/products/12345")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert "coupang.com" in (result.site_name or "")


# 일반 웹 스크래퍼 테스트

class TestWebScraper:
    """일반 웹 스크래퍼 테스트"""

    @pytest.mark.asyncio
    async def test_scrape_web_returns_scrape_response(self):
        result = await scrape_web("https://en.wikipedia.org/wiki/Python_(programming_language)")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert result.title is not None

    @pytest.mark.asyncio
    async def test_scrape_web_invalid_url(self):
        result = await scrape_web("https://this-domain-does-not-exist-12345.com")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True  # basic metadata fallback


# 통합 테스트 (scrape_url)

class TestScrapeUrlIntegration:
    """scrape_url 메인 함수의 ScrapeResponse 반환 테스트"""

    @pytest.mark.asyncio
    async def test_empty_url(self):
        result = await scrape_url("")
        assert isinstance(result, ScrapeResponse)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_google_search_url(self, monkeypatch):
        class FailingAsyncClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def head(self, *args, **kwargs):
                raise RuntimeError("network disabled for test")

        monkeypatch.setattr(scrape_orchestrator, "validate_url_safety", lambda url: True)
        monkeypatch.setattr(scrape_orchestrator, "normalize_url", lambda url: url)
        monkeypatch.setattr(scrape_orchestrator.httpx, "AsyncClient", FailingAsyncClient)
        monkeypatch.setattr(
            scrape_orchestrator,
            "scrape_google_search",
            lambda url: ScrapeResponse(
                success=True,
                title="test | Google 검색",
                description="'test'의 Google 검색 결과입니다.",
                site_name="Google",
                url=url,
                content="",
            ),
        )

        result = await scrape_url("https://www.google.com/search?q=test")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert result.site_name == "Google"

    @pytest.mark.asyncio
    async def test_naver_search_url(self):
        result = await scrape_url("https://search.naver.com/search.naver?query=테스트")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_generic_web_url(self):
        result = await scrape_url("http://quotes.toscrape.com/")
        assert isinstance(result, ScrapeResponse)
        assert result.success is True
        assert result.title is not None
