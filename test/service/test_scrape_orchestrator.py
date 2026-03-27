"""
스크래프 오케스트레이터 테스트
"""

import pytest

from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.service import scrape_orchestrator


class _FailingAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def head(self, *args, **kwargs):
        raise RuntimeError("network disabled for test")


@pytest.mark.asyncio
async def test_scrape_url_empty_url_returns_error():
    result = await scrape_orchestrator.scrape_url("")
    assert isinstance(result, ScrapeResponse)
    assert result.success is False


@pytest.mark.asyncio
async def test_scrape_url_delegates_google_search(monkeypatch):
    monkeypatch.setattr(scrape_orchestrator, "validate_url_safety", lambda url: True)
    monkeypatch.setattr(scrape_orchestrator, "normalize_url", lambda url: url)
    monkeypatch.setattr(scrape_orchestrator.httpx, "AsyncClient", _FailingAsyncClient)
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

    result = await scrape_orchestrator.scrape_url("https://www.google.com/search?q=test")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert result.site_name == "Google"


@pytest.mark.asyncio
async def test_scrape_url_delegates_naver_search(monkeypatch):
    monkeypatch.setattr(scrape_orchestrator, "validate_url_safety", lambda url: True)
    monkeypatch.setattr(scrape_orchestrator, "normalize_url", lambda url: url)
    monkeypatch.setattr(scrape_orchestrator.httpx, "AsyncClient", _FailingAsyncClient)
    monkeypatch.setattr(
        scrape_orchestrator,
        "scrape_naver_search",
        lambda url: ScrapeResponse(
            success=True,
            title="테스트 | 네이버 검색",
            description="네이버 검색 결과입니다.",
            site_name="Naver",
            url=url,
            content="",
        ),
    )

    result = await scrape_orchestrator.scrape_url(
        "https://search.naver.com/search.naver?query=테스트"
    )
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert result.site_name == "Naver"


@pytest.mark.asyncio
async def test_scrape_url_delegates_generic_web(monkeypatch):
    url = "http://quotes.toscrape.com/"
    monkeypatch.setattr(scrape_orchestrator, "validate_url_safety", lambda url: True)
    monkeypatch.setattr(scrape_orchestrator, "normalize_url", lambda url: url)
    monkeypatch.setattr(scrape_orchestrator.httpx, "AsyncClient", _FailingAsyncClient)

    async def fake_scrape_web(url, include_content=True, max_length=1000):
        return ScrapeResponse(
            success=True,
            title="Quotes to Scrape",
            description="Sample quote site",
            site_name="Quotes to Scrape",
            url=url,
            content="A meaningful quote body",
        )

    monkeypatch.setattr(scrape_orchestrator, "scrape_web", fake_scrape_web)
    result = await scrape_orchestrator.scrape_url(url=url)

    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert "Quotes to Scrape" in (result.title or "")


@pytest.mark.asyncio
async def test_scrape_url_preserves_web_content(monkeypatch):
    url = "https://en.wikipedia.org/wiki/Load_testing"
    monkeypatch.setattr(scrape_orchestrator, "validate_url_safety", lambda url: True)
    monkeypatch.setattr(scrape_orchestrator, "normalize_url", lambda url: url)
    monkeypatch.setattr(scrape_orchestrator.httpx, "AsyncClient", _FailingAsyncClient)

    async def fake_scrape_web(url, include_content=True, max_length=1000):
        return ScrapeResponse(
            success=True,
            title="Load testing - Wikipedia",
            description="Wikipedia article",
            site_name="Wikipedia",
            url=url,
            content="Load testing is the process of putting demand on a system and measuring its response.",
        )

    monkeypatch.setattr(scrape_orchestrator, "scrape_web", fake_scrape_web)
    result = await scrape_orchestrator.scrape_url(url=url)

    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert "Load testing" in (result.title or "")
    assert len(result.content or "") > 50
