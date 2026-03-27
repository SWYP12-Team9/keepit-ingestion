"""
기본 웹 서비스 테스트
"""

import pytest

from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.service.platform.web_service import scrape_web


@pytest.mark.asyncio
async def test_scrape_web_returns_scrape_response():
    result = await scrape_web("https://en.wikipedia.org/wiki/Python_(programming_language)")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
    assert result.title is not None


@pytest.mark.asyncio
async def test_scrape_web_invalid_url_falls_back_to_basic_metadata():
    result = await scrape_web("https://this-domain-does-not-exist-12345.com")
    assert isinstance(result, ScrapeResponse)
    assert result.success is True
