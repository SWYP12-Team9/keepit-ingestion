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
import asyncio
from app.scrapers.utils.headers import get_browser_headers


def scrape_url(url: str, include_content: bool = True, max_length: int = 1000) -> Dict[str, Any]:
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

    Examples:
        >>> result = scrape_url("https://www.youtube.com/watch?v=...")
        >>> print(result["title"])
        >>> print(result["transcript"][:100])

        >>> result = scrape_url("https://velog.io/@user/post")
        >>> print(result["description"])
    """
    # URL 검증
    if not url:
        return {
            "success": False,
            "error": "URL is required"
        }
        
    # SSRF 방지: 로컬/사설 IP 차단 -> 차단 시 Fallback 메타데이터 반환
    if not validate_url_safety(url):
        return generate_basic_metadata(url)

    # URL 정규화
    url = normalize_url(url)

    # 리다이렉트를 따라가서 최종 URL 확인
    # 축약 URL (예: https://share.google/...) 이 다른 URL로 리다이렉트될 수 있으므로
    final_url = url
    try:
        import requests
        # 실제 브라우저와 유사한 헤더 생성
        headers = get_browser_headers()
        # HEAD 요청으로 가볍게 최종 URL만 확인 (타임아웃 짧게)
        response = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        if response.status_code < 400:
            final_url = response.url
        else:
            final_url = url
    except Exception:
        # 리다이렉트 확인 실패시 원본 URL 사용
        final_url = url

    # 사이트별 스크래퍼 선택
    if is_youtube_url(final_url):
        result = scrape_youtube(final_url, include_content=include_content)
    elif is_instagram_url(final_url):
        result = scrape_instagram(final_url, max_length=max_length)
    elif is_google_search_url(final_url):
        result = scrape_google_search(final_url)
    elif is_naver_search_url(final_url):    
        result = scrape_naver_search(final_url)
    elif is_daum_search_url(final_url):
        result = scrape_daum_search(final_url)
    elif is_naver_map_url(final_url):
        result = scrape_naver_map(final_url)
    elif is_naver_blog_url(final_url):
        from .naver import scrape_naver_blog
        result = scrape_naver_blog(final_url)
    elif is_coupang_url(final_url):
        result = scrape_coupang(final_url)
        return result
    else:
        result = scrape_web(final_url, include_content=True, max_length=max_length)

    # title이 없거나, content와 description 둘 다 없을 때 추가 처리
    title = result.get("title") or "" if result else ""
    content = result.get("content") or "" if result else ""
    description = result.get("description") or "" if result else ""
    
    # Title을 가져왔지만 Content가 없는 경우 -> Playwright 시도 (JS 렌더링 필요 가능성)
    if title.strip() and not content.strip():
        logger.info("Title found but content missing. Attempting Playwright scraping...")
        try:
            # 비동기 함수이므로 동기 환경에서 실행하기 위한 처리
            # 주의: 이미 비동기 루프 내부라면 await 사용해야 함. 
            # 현재 구조상 scrape_url이 동기 함수이므로 asyncio.run 사용
            from .playwright_scraper import scrape_with_playwright
            playwright_result = asyncio.run(scrape_with_playwright(final_url))
            
            if playwright_result and playwright_result.get("content"):
                logger.info("Playwright scraping successful.")
                return playwright_result
            elif playwright_result:
                 # Playwright로도 콘텐츠 못 찾았지만 메타데이터는 있을 수 있음
                 # 기존 result보다 나은지 확인 필요하지만, 일단 Playwright 결과가 있으면 사용
                 if playwright_result.get("title"):
                     # 여기선 Playwright 결과가 성공적(title 있음)이면 대체
                     result = playwright_result
        except Exception as e:
            logger.error(f"Playwright scraping failed: {e}")
            # 실패하면 기존 result 유지 (title은 있으니까)

    # 갱신된 result 확인
    title = result.get("title") or "" if result else ""
    content = result.get("content") or "" if result else ""
    description = result.get("description") or "" if result else ""

    # CASE 2: Title조차 없거나, 여전히 Content/Description이 부실한 경우 -> Apify 시도
    if not result or not title.strip() or (not content.strip() and not description.strip()):
        logger.info("Insufficient metadata. Attempting Apify scraping...")
        try:
            from .apify_scraper import scrape_with_apify
            apify_result = scrape_with_apify(final_url)
            if apify_result and apify_result.get("title"):
                return apify_result
        except Exception as e:
            # Apify 시도 중 에러는 무시하고 기본값 반환
            logger.error(f"Apify scraping failed: {e}")
            
        return generate_basic_metadata(final_url)

    return result
