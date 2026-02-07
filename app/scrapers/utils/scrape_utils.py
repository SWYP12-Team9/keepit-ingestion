"""
스크래퍼 유틸리티 함수 모듈

URL 분석, 정규화 등의 공통 유틸리티 함수들을 제공합니다.
"""

from typing import Optional
from urllib.parse import urlparse
import socket
import ipaddress
import os


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
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain == "youtu.be":
            return True
        if domain == "youtube.com" or domain == "m.youtube.com":
            return True
        return False
    except:
        return False


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


def is_google_search_url(url: str) -> bool:
    """
    Google URL(검색 또는 메인)인지 확인합니다.

    Args:
        url: 확인할 URL

    Returns:
        Google 관련 URL이면 True, 아니면 False
    """
    return "google.com/" in url or "google.co.kr" in url or url.endswith("google.com") or url.endswith("google.co.kr")


def is_coupang_url(url: str) -> bool:
    """
    Coupang URL인지 확인합니다.

    Args:
        url: 확인할 URL

    Returns:
        Coupang URL이면 True, 아니면 False
    """
    return "coupang.com/" in url or url.endswith("coupang.com")


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
    elif is_google_search_url(url):
        return "google_search"
    elif is_coupang_url(url):
        return "coupang"
    else:
        return "generic"





def generate_basic_metadata(url: str) -> dict:
    """
    스크래핑 실패/차단 시 사용할 대체 메타데이터를 생성합니다.
    URL의 도메인에서 사이트 이름을 추출하여 제목으로 사용합니다.

    Args:
        url: 원본 URL

    Returns:
        dict: 대체 메타데이터
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # www. 제거
        if domain.startswith("www."):
            domain = domain[4:]
            
        # .com, .co.kr 등 제거 로직 삭제 -> 도메인 그대로 사용
        site_name = domain

        return {
            "success": True,
            "title": site_name, # 도메인 그대로 사용 (예: coupang.com)
            "description": "",
            "thumbnail_url": None,
            "favicon_url": f"{parsed.scheme}://{parsed.netloc}/favicon.ico",
            "site_name": site_name,
            "url": url,
            "content": ""
        }
    except Exception:
        # URL 파싱 실패 등 최악의 경우
        return {
            "success": True, # 실패로 처리하지 않고 기본값 반환
            "title": "Website",
            "description": "",
            "thumbnail_url": None,
            "favicon_url": None,
            "site_name": "Website",
            "url": url,
            "content": ""
        }

def validate_url_safety(url: str) -> bool:
    """
    URL이 안전한지 검증합니다 (SSRF 방지).
    로컬 네트워크(localhost, 127.0.0.1, 192.168.x.x 등)로의 요청을 차단합니다.
    단, SSRF_ALLOWLIST 환경변수에 지정된 호스트는 허용합니다.

    Args:
        url: 검증할 URL

    Returns:
        bool: 안전하면 True, 아니면 False
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            return False

        # 포트 검사: 80, 443 이외의 포트 차단
        if parsed.port and parsed.port not in [80, 443]:
            return False

        # Allowlist 확인
        allowlist = os.environ.get("SSRF_ALLOWLIST", "")
        if allowlist:
            allowed_hosts = [host.strip() for host in allowlist.split(",") if host.strip()]
            if hostname in allowed_hosts:
                return True

        # Blocklist 확인
        blocklist = os.environ.get("URL_BLOCKLIST", "")
        if blocklist:
            blocked_hosts = [host.strip() for host in blocklist.split(",") if host.strip()]
            for blocked_host in blocked_hosts:
                # 와일드카드 패턴 (*.example.com)
                if blocked_host.startswith("*."):
                    domain_part = blocked_host[2:] # *. 제거
                    if hostname == domain_part or hostname.endswith("." + domain_part):
                        return False
                # 정확한 일치 (example.com)
                elif hostname == blocked_host:
                    return False
            
        # IP 주소인지 확인
        try:
            ip = ipaddress.ip_address(hostname)
        except ValueError:
            # IP가 아니면 도메인 이름 해석
            try:
                ip_str = socket.gethostbyname(hostname)
                ip = ipaddress.ip_address(ip_str)
            except socket.gaierror:
                return False # 도메인 해석 실패 시 안전하지 않은 것으로 간주 (또는 실패 처리)

        # 사설 IP 또는 루프백 IP 차단
        if ip.is_private or ip.is_loopback:
            return False
            
        return True
    except Exception:
        return False

