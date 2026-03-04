
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import trafilatura
from playwright.async_api import async_playwright, Browser, Playwright
from app.scrapers.utils.scrape_utils import generate_basic_metadata
from app.scrapers.service.web import extract_meta_tags

logger = logging.getLogger(__name__)


from dataclasses import dataclass

@dataclass
class BrowserInstance:
    browser: Browser
    usage_count: int = 0

class BrowserPool:
    def __init__(self, pool_size: int = 2, max_usages: int = 100):
        self.pool_size = pool_size
        self.max_usages = max_usages
        self._playwright: Optional[Playwright] = None
        self._browsers: List[Browser] = []
        self._queue: Optional[asyncio.Queue[BrowserInstance]] = None

    async def initialize(self):
        """앱 시작 시 브라우저를 pool_size만큼 미리 생성합니다."""
        self._playwright = await async_playwright().start()
        self._queue = asyncio.Queue()
        for _ in range(self.pool_size):
            browser = await self._launch_browser()
            self._browsers.append(browser)
            await self._queue.put(BrowserInstance(browser=browser))
        logger.info(f"BrowserPool initialized with {self.pool_size} browsers.")

    async def _launch_browser(self) -> Browser:
        assert self._playwright is not None, "BrowserPool not initialized. Call initialize() first."
        return await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

    @asynccontextmanager
    async def acquire(self):
        """풀에서 브라우저를 하나 빌리고, 새 context를 생성해 제공합니다.
        사용 완료 후 context는 닫고 브라우저는 풀에 주기적으로 판별하여 반납 및 재생성합니다."""
        assert self._queue is not None, "BrowserPool not initialized. Call initialize() first."
        browser_item = await self._queue.get()
        browser = browser_item.browser
        context = None
        try:
            # 브라우저 크래시 감지 및 복구
            if not browser.is_connected():
                logger.warning("Browser disconnected. Relaunching...")
                try:
                    self._browsers.remove(browser)
                except ValueError:
                    pass
                browser = await self._launch_browser()
                self._browsers.append(browser)
                browser_item.browser = browser
                browser_item.usage_count = 0

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
            )
            yield context
        finally:
            if context:
                await context.close()
                
            # 리소스 누수 방지를 위한 주기적 브라우저 재시작
            browser_item.usage_count += 1
            if browser_item.usage_count >= self.max_usages:
                logger.info(f"Browser reached maximum usage limit ({self.max_usages}). Restarting to prevent memory leaks...")
                try:
                    if browser in self._browsers:
                        self._browsers.remove(browser)
                    await browser.close()
                except Exception as e:
                    logger.warning(f"Error closing browser during recycle: {e}")
                
                try:
                    new_browser = await self._launch_browser()
                    self._browsers.append(new_browser)
                    browser_item.browser = new_browser
                    browser_item.usage_count = 0
                except Exception as e:
                    logger.error(f"Failed to relaunch browser during recycle: {e}")
                    # 만약 실패하더라도 객체는 큐에 들어감 (다음 acquire 때 is_connected=False 로 잡혀 복구됨)

            await self._queue.put(browser_item)

    async def close(self):
        """앱 종료 시 모든 브라우저를 닫습니다."""
        for browser in self._browsers:
            try:
                await browser.close()
            except Exception:
                pass
        if self._playwright is not None:
            await self._playwright.stop()
        logger.info("BrowserPool closed.")


# 앱 전체에서 공유하는 싱글톤 인스턴스
browser_pool = BrowserPool(pool_size=2)


async def scrape_with_playwright(url: str, max_length: int = 2000) -> Optional[Dict[str, Any]]:
    """
    풀에서 브라우저 context를 빌려 JavaScript 기반 웹페이지를 스크래핑합니다.

    Args:
        url: 스크래핑할 URL
        max_length: 본문 최대 길이

    Returns:
        성공 시 메타데이터 딕셔너리, 실패 시 None
    """
    logger.info(f"Playwright scraping started for: {url}")

    try:
        async with browser_pool.acquire() as context:
            page = await context.new_page()
            # 리소스 최적화: 불필요한 이미지, 폰트 로딩 차단
            await page.route("**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,otf}", lambda route: route.abort())

            try:
                # 1단계: 기본적인 HTML 로드 상태(load)까지 짧게 대기 (최대 7초)
                # 대부분의 사이트는 1~2초 내에 이 단계에 도달합니다.
                try:
                    await page.goto(url, wait_until="load", timeout=7000)
                except Exception as e:
                    logger.warning(f"Initial load timeout for {url}: {str(e)}. Proceeding with partial content.")

                # 2단계: 추가적인 JS 렌더링을 위해 네트워크 유휴 상태를 딱 3초만 더 관찰
                # 렌더링이 완료되면 3초를 다 채우지 않고 즉시 반환됩니다.
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    # 3초가 지나도 네트워크가 활성 상태면(광고 등), 그냥 무시하고 현재 DOM을 가져옴
                    logger.info(f"Network didn't settle for {url} within 3s, extracting current DOM.")

                # 최종 렌더링된 HTML 추출
                content_html = await page.content()

            except Exception as e:
                logger.warning(f"Playwright page load warning for {url}: {str(e)}")
                # 에러가 나더라도 현재까지 로드된 HTML이라도 가져와봄
                try:
                    content_html = await page.content()
                except Exception:
                    content_html = ""
            finally:
                await page.close()

            if not content_html:
                return None

            soup = BeautifulSoup(content_html, "html.parser")

            metadata = await extract_meta_tags(soup, url)

            result = {
                "success": True,
                "title": metadata.get("title"),
                "description": metadata.get("description"),
                "thumbnail_url": metadata.get("thumbnail_url"),
                "favicon_url": metadata.get("icon"),
                "site_name": metadata.get("site_name"),
                "url": url,
            }

            content = trafilatura.extract(content_html, include_comments=False)
            if content:
                result["content"] = content[:max_length] if len(content) > max_length else content

            return result

    except Exception as e:
        logger.error(f"Playwright scraping failed: {str(e)}")
        return None
