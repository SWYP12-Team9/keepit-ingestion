"""
URL 메타데이터 스크래퍼 메인 모듈

다양한 웹사이트의 URL에서 title, description, 대표 이미지를 추출합니다.
함수 기반 접근으로 간단하고 확장 가능한 구조를 제공합니다.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
from .web import scrape_web
from .youtube import scrape_youtube
from .instagram import scrape_instagram
from .google import scrape_google_search
from .coupang import scrape_coupang
from .naver import scrape_naver_map, scrape_naver_search
from .daum import scrape_daum_search
from .playwright_scraper import scrape_with_playwright
from app.scrapers.utils.scrape_utils import (
    detect_site_type,
    validate_url_safety,
    generate_basic_metadata,
    normalize_url,
    is_youtube_url,
    is_instagram_url,
    is_naver_blog_url,
    is_velog_url,
    is_tistory_url,
    is_google_search_url,
    is_naver_search_url,
    is_daum_search_url,
    is_naver_map_url,
    is_coupang_url
)
import httpx
from app.scrapers.utils.headers import get_browser_headers


async def scrape_url(url: str, include_content: bool = True, max_length: int = 1000) -> Dict[str, Any]:
    """
    URL에서 메타데이터를 추출하는 메인 함수.

    지원 사이트:
    - YouTube (자막 포함)
    - Instagram (Open Graph 태그 사용)
    - 네이버 블로그
    - 벨로그 (velog.io)
    - 티스토리
    - 쿠팡
    - 페이스북
    - 일반 웹사이트 (Open Graph, Twitter Card 지원)

    Args:
        url: 스크래핑할 URL
        include_content: YouTube 자막 포함 여부 (기본값: True)
        max_length: 본문 미리보기 최대 길이 (기본값: 1000)

    Returns:
        dict: {
            "success": bool,
            "title": str,
            "description": str,
            "thumbnail_url": str,
            "favicon_url": str,
            "site_name": str,
            "url": str,
            "content": str (YouTube만, include_content=True인 경우),
            ...
        }
    """
    if not url:
        return {
            "success": False,
            "error": "URL is required"
        }

    # SSRF 방지: 로컬/사설 IP 차단
    if not validate_url_safety(url):
        return generate_basic_metadata(url)

    # URL 정규화
    url = normalize_url(url)

    # 축약 URL 리다이렉트 추적으로 최종 URL 확인
    final_url = url
    try:
        headers = get_browser_headers()
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.head(url, headers=headers, timeout=5)
        if response.status_code < 400:
            final_url = str(response.url)
        else:
            final_url = url
    except Exception:
        final_url = url

    # 사이트별 스크래퍼 선택
    if is_youtube_url(final_url):
        result = await scrape_youtube(final_url, include_content=include_content)
    elif is_instagram_url(final_url):
        result = await scrape_instagram(final_url, max_length=max_length)
    elif is_google_search_url(final_url):
        result = scrape_google_search(final_url)
    elif is_naver_search_url(final_url):
        result = scrape_naver_search(final_url)
    elif is_daum_search_url(final_url):
        result = scrape_daum_search(final_url)
    elif is_naver_map_url(final_url):
        result = await scrape_naver_map(final_url)
    elif is_naver_blog_url(final_url):
        from .naver import scrape_naver_blog
        result = await scrape_naver_blog(final_url)
    elif is_coupang_url(final_url):
        result = scrape_coupang(final_url)
        return result
    else:
        result = await scrape_web(final_url, include_content=True, max_length=max_length)

    title = result.get("title") or "" if result else ""
    content = result.get("content") or "" if result else ""
    description = result.get("description") or "" if result else ""

    # Content가 없거나 100자 미만인 경우 → Playwright 시도
    if not content.strip() or len(content.strip()) < 100:
        logger.info("Content missing or too short. Attempting Playwright scraping...")
        try:
            playwright_result = await scrape_with_playwright(final_url)

            if playwright_result and playwright_result.get("content"):
                logger.info("Playwright scraping successful.")
                return playwright_result
            elif playwright_result and playwright_result.get("title"):
                result = playwright_result
        except Exception as e:
            logger.error(f"Playwright scraping failed: {e}")

    title = result.get("title") or "" if result else ""
    content = result.get("content") or "" if result else ""
    description = result.get("description") or "" if result else ""

    # Title조차 없거나 Content/Description 모두 없는 경우 → Apify 시도
    if not result or not title.strip() or (not content.strip() and not description.strip()):
        logger.info("Insufficient metadata. Attempting Apify scraping...")
        # try: # todo: 잠깐 주석처리
        #     from .apify_scraper import scrape_with_apify
        #     apify_result = await scrape_with_apify(final_url)
        #     if apify_result and apify_result.get("title"):
        #         return apify_result
        # except Exception as e:
        #     logger.error(f"Apify scraping failed: {e}")

        return generate_basic_metadata(final_url)

    return result
