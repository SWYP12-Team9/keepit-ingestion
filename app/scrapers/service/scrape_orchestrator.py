"""
URL 스크래핑 오케스트레이터 모듈

URL 유형을 판별하고 적절한 플랫폼 서비스 또는 기본 웹 서비스로 위임합니다.
"""

import logging

logger = logging.getLogger(__name__)
from .platform.web_service import scrape_web
from .platform.youtube_service import scrape_youtube
from .platform.instagram_service import scrape_instagram
from .platform.google_service import scrape_google_search
from .platform.coupang_service import scrape_coupang
from .platform.naver_service import (
    scrape_naver_map,
    scrape_naver_search,
    scrape_naver_blog,
)
from .platform.daum_service import scrape_daum_search
from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.utils.scrape_utils import (
    validate_url_safety,
    generate_basic_metadata,
    normalize_url,
    is_youtube_url,
    is_instagram_url,
    is_naver_blog_url,
    is_google_search_url,
    is_naver_search_url,
    is_daum_search_url,
    is_naver_map_url,
    is_coupang_url,
)
import httpx
from app.scrapers.utils.headers import get_browser_headers


async def scrape_url(
    url: str,
    include_content: bool = True,
    max_length: int = 1000,
) -> ScrapeResponse:
    """
    URL에서 메타데이터를 추출하는 메인 함수.

    Args:
        url: 스크래핑할 URL
        include_content: YouTube 자막 포함 여부 (기본값: True)
        max_length: 본문 미리보기 최대 길이 (기본값: 1000)

    Returns:
        ScrapeResponse
    """
    if not url:
        return ScrapeResponse(success=False, error="URL is required")

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
        result = await scrape_naver_blog(final_url)
    elif is_coupang_url(final_url):
        result = scrape_coupang(final_url)
        return result
    else:
        result = await scrape_web(final_url, include_content=True, max_length=max_length)

    title = result.title or ""
    content = result.content or ""
    description = result.description or ""

    # Title조차 없거나 Content/Description 모두 없는 경우 → 기본 메타데이터 반환
    if not title.strip() or (not content.strip() and not description.strip()):
        logger.info("Insufficient metadata. Returning basic metadata.")
        return generate_basic_metadata(final_url)

    return result
