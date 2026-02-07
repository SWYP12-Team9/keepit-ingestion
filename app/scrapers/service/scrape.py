"""
URL 메타데이터 스크래퍼 메인 모듈

다양한 웹사이트의 URL에서 title, description, 대표 이미지를 추출합니다.
함수 기반 접근으로 간단하고 확장 가능한 구조를 제공합니다.
"""

from typing import Dict, Any
from .web import scrape_web
from .youtube import scrape_youtube
from .instagram import scrape_instagram
from .google import scrape_google_search
from .coupang import scrape_coupang
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
        final_url = response.url
    except Exception:
        # 리다이렉트 확인 실패시 원본 URL 사용
        final_url = url

    # YouTube URL 처리 (최종 URL 기준)
    if is_youtube_url(final_url):
        return scrape_youtube(final_url, include_content=include_content)

    # Instagram URL 처리 (최종 URL 기준)
    if is_instagram_url(final_url):
        return scrape_instagram(final_url, max_length=max_length)

    # Google Search URL 처리 (최종 URL 기준)
    if is_google_search_url(final_url):
        return scrape_google_search(final_url)

    # Coupang URL 처리 (최종 URL 기준)
    if is_coupang_url(final_url):
        return scrape_coupang(final_url)

    # 일반 웹사이트 처리 (최종 URL 사용)
    return scrape_web(final_url, include_content=True, max_length=max_length)
