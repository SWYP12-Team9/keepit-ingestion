"""
웹 스크래핑 서비스 모듈

정적 및 동적 스크래핑 전략을 조합해
웹페이지 메타데이터와 본문 추출 결과를 반환합니다.
"""

import logging
import httpx
from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.utils.scrape_utils import generate_basic_metadata
from app.scrapers.service.strategy import scrape_static, scrape_dynamic

logger = logging.getLogger(__name__)

async def scrape_web(url: str, include_content: bool = True, max_length: int = 1000) -> ScrapeResponse:
    """
    웹페이지에서 메타데이터를 추출합니다. 
    1순위로 정적 스크래핑을 시도하고, 본문이 부실할 경우 2순위로 동적(JS 렌더링) 스크래핑을 수행합니다.

    Args:
        url: 웹페이지 URL
        include_content: 본문 내용 추출 여부
        max_length: 본문 미리보기 최대 길이

    Returns:
        ScrapeResponse
    """
    try:
        # 1. 정적 스크래핑 시도 (Fast & Efficient)
        result = await scrape_static(url, include_content=include_content, max_length=max_length)
        
        # 2. 결과가 부실한 경우 동적 스크래핑으로 폴백 (JS/SPA 사이트 지원)
        _content_str = result.content or ""
        should_try_dynamic = (
            result.force_dynamic_render
            or not _content_str.strip()
            or len(_content_str.strip()) < 100
        )
        if should_try_dynamic:
            if result.force_dynamic_render:
                logger.info(
                    "Static HTML indicates JS rendering is required. "
                    "Attempting dynamic scraping (reason=%s)...",
                    result.dynamic_render_reason or "unknown",
                )
            else:
                logger.info("Content missing or too short. Attempting dynamic scraping (SPA support)...")
            try:
                dynamic_result = await scrape_dynamic(url, max_length=max_length)
                
                if dynamic_result and dynamic_result.content:
                    logger.info("Dynamic scraping successful.")
                    return dynamic_result
                elif dynamic_result and dynamic_result.title:
                    # 마땅한 본문이 없더라도 동적 스크래핑으로 얻은 제목 등이 더 정확할 수 있음
                    result = dynamic_result
            except Exception as e:
                logger.error(f"Dynamic scraping failed: {e}")

        return result

    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning(f"Static scraping request failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
    except Exception as e:
        logger.error(f"Scraping process failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
