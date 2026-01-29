"""
스크래퍼 유틸리티 함수 모듈

URL 분석, 정규화 등의 공통 유틸리티 함수들을 제공합니다.
"""

from typing import Optional


def normalize_url(url: str) -> str:
    """
    URL을 정규화합니다.

    Args:
        url: 정규화할 URL

    Returns:
        정규화된 URL (http:// 또는 https:// 포함)
    """
    if not url:
        return url

    if not url.startswith(('http://', 'https://')):
        return 'https://' + url

    return url


def is_youtube_url(url: str) -> bool:
    """
    YouTube URL인지 확인합니다.

    Args:
        url: 확인할 URL

    Returns:
        YouTube URL이면 True, 아니면 False
    """
    return "youtube.com" in url or "youtu.be" in url


def is_instagram_url(url: str) -> bool:
    """
    Instagram URL인지 확인합니다.

    Args:
        url: 확인할 URL

    Returns:
        Instagram URL이면 True, 아니면 False
    """
    return "instagram.com" in url


def is_naver_blog_url(url: str) -> bool:
    """
    네이버 블로그 URL인지 확인합니다.

    Args:
        url: 확인할 URL

    Returns:
        네이버 블로그 URL이면 True, 아니면 False
    """
    return "blog.naver.com" in url


def is_velog_url(url: str) -> bool:
    """
    Velog URL인지 확인합니다.

    Args:
        url: 확인할 URL

    Returns:
        Velog URL이면 True, 아니면 False
    """
    return "velog.io" in url


def is_tistory_url(url: str) -> bool:
    """
    티스토리 URL인지 확인합니다.

    Args:
        url: 확인할 URL

    Returns:
        티스토리 URL이면 True, 아니면 False
    """
    return "tistory.com" in url


def detect_site_type(url: str) -> str:
    """
    URL에서 사이트 타입을 감지합니다.

    Args:
        url: 확인할 URL

    Returns:
        사이트 타입 ("youtube", "instagram", "naver_blog", "velog", "tistory", "generic")
    """
    if is_youtube_url(url):
        return "youtube"
    elif is_instagram_url(url):
        return "instagram"
    elif is_naver_blog_url(url):
        return "naver_blog"
    elif is_velog_url(url):
        return "velog"
    elif is_tistory_url(url):
        return "tistory"
    else:
        return "generic"
