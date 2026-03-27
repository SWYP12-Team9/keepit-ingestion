"""
동적 스크래핑 전략 모듈

JS 렌더링이 필요한 웹페이지를 위한 전략 인터페이스를 제공합니다.
외부 모듈은 이 모듈의 `scrape_dynamic`만 호출하고 구현체 세부 사항은 알지 않습니다.
"""

from typing import Optional
import logging
from app.scrapers.dto.scrape_response import ScrapeResponse

# 현재는 Playwright 프로바이더를 기본 동적 엔진으로 사용합니다.
from app.scrapers.service.provider.playwright_provider import scrape_with_playwright

logger = logging.getLogger(__name__)

async def scrape_dynamic(url: str, max_length: int = 2000) -> Optional[ScrapeResponse]:
    """
    JS 기반 렌더링이 필요한 웹페이지에서 내용을 추출합니다.
    내부적으로 Playwright 등의 동적 렌더링 엔진을 사용합니다.
    
    Args:
        url: 스크래핑할 웹사이트 URL
        max_length: 본문 최대 추출 길이
        
    Returns:
        ScrapeResponse: 메타데이터와 렌더링된 본문 내용을 포함한 결과. 
                      렌더링 실패 시 None 반환.
    """
    return await scrape_with_playwright(url, max_length=max_length)

__all__ = ["scrape_dynamic"]
