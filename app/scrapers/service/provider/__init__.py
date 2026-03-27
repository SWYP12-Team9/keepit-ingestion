"""
스크래퍼 프로바이더 패키지

실제 동작을 담당하는 인프라스텍처 계층으로,
Playwright, Apify 등의 클라이언트를 포함합니다.
"""

from .playwright_provider import scrape_with_playwright, browser_pool, BrowserPool
from .apify_provider import scrape_with_apify

__all__ = ["scrape_with_playwright", "browser_pool", "BrowserPool", "scrape_with_apify"]
