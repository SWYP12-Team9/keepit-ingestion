"""기존 통합 테스트 - ScrapeResponse 반환 타입에 맞게 업데이트"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
async def test_scrape_quote_toscrape(monkeypatch):
    """일반 웹 URL이 web 스크래퍼로 위임되는지 검증"""
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
async def test_scrape_wikipedia(monkeypatch):
    """일반 웹 URL 본문 결과가 유지되는지 검증"""
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
    assert len(result.content or "") > 50, "Content should have some text"
