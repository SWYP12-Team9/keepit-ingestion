
import logging
import asyncio
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import trafilatura
from playwright.async_api import async_playwright
from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)

async def scrape_with_playwright(url: str, max_length: int = 2000) -> Optional[Dict[str, Any]]:
    """
    Playwright를 사용하여 JavaScript 기반 웹페이지를 스크래핑합니다.
    주로 정적 스크래핑으로 본문을 가져오지 못한 경우에 사용됩니다.

    Args:
        url: 스크래핑할 URL
        max_length: 본문 최대 길이

    Returns:
        성공 시 메타데이터 딕셔너리, 실패 시 None
    """
    logger.info(f"Playwright scraping started for: {url}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    viewport={'width': 1280, 'height': 800}
                )
                
                page = await context.new_page()
                
                # 페이지 로드 (타임아웃 30초)
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    # 약간의 추가 대기 (동적 로딩)
                    await page.wait_for_timeout(2000)
                    
                    # iframe이 있는 경우 탐색 시도
                    frames = page.frames
                    if len(frames) > 1:
                        logger.info(f"Checking {len(frames)} frames for content...")
                        
                    content_html = await page.content()
                    
                except Exception as e:
                    logger.warning(f"Playwright page load warning: {str(e)}")
                    # 부분 로드라도 시도하기 위해 content 가져옴
                    if 'page' in locals():
                        content_html = await page.content()
                    else:
                        content_html = ""
            finally:
                await browser.close()
            
            # HTML 파싱 및 메타데이터 추출
            if not content_html:
                return None

            soup = BeautifulSoup(content_html, 'html.parser')
            
            # 메타데이터 추출 (기존 로직 활용을 위해 재구현하거나 import)
            from app.scrapers.service.web import extract_meta_tags
            metadata = extract_meta_tags(soup, url)
            
            result = {
                "success": True,
                "title": metadata.get("title"),
                "description": metadata.get("description"),
                "thumbnail_url": metadata.get("thumbnail_url"),
                "favicon_url": metadata.get("icon"),
                "site_name": metadata.get("site_name"),
                "url": url,
            }
            
            # 본문 추출
            content = trafilatura.extract(content_html, include_comments=False)
            if content:
                result["content"] = content[:max_length] if len(content) > max_length else content
            
            return result
            
    except Exception as e:
        logger.error(f"Playwright scraping failed: {str(e)}")
        return None
