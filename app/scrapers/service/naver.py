"""
Naver 서비스(지도, 검색) 핸들러 모듈

Naver 지도 및 검색 URL에서 쿼리나 장소명을 추출하여 메타데이터를 생성합니다.
복잡한 스크래핑을 피하고 URL 분석을 통해 즉각적인 응답을 제공합니다.
"""

import logging
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs
from .web import scrape_web

import re
from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)

def preprocess_naver_blog_url(url: str) -> str:
    """
    네이버 블로그 URL을 스크래핑 가능한 형태로 변환합니다.
    (iframe 구조를 회피하기 위해 PostView URL로 변환)
    """
    pattern = r"blog\.naver\.com/([a-zA-Z0-9_-]+)/([0-9]+)"
    match = re.search(pattern, url)
    if match:
        blog_id = match.group(1)
        log_no = match.group(2)
        return f"https://blog.naver.com/PostView.naver?blogId={blog_id}&logNo={log_no}"

    return url

async def scrape_naver_blog(url: str) -> Dict[str, Any]:
    """
    네이버 블로그 URL을 스크래핑합니다.
    iframe 구조를 처리하기 위해 URL 전처리를 수행 후 일반 웹 스크래퍼를 호츨합니다.
    """
    try:
        target_url = preprocess_naver_blog_url(url)
        return await scrape_web(target_url)

    except Exception as e:
        logger.error(f"Failed to scrape Naver Blog: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)

async def scrape_naver_map(url: str) -> Dict[str, Any]:
    """
    Naver 지도 URL에서 메타데이터를 추출합니다.
    """
    try:
        result = await scrape_web(url)
        if not result.get("title"):
            result["title"] = "네이버 지도"
            result["site_name"] = "Naver"
        return result
    except Exception as e:
        logger.error(f"Failed to scrape Naver Map: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)

def scrape_naver_search(url: str) -> Dict[str, Any]:
    """
    Naver 검색 URL에서 검색어를 추출합니다.

    URL 구조 예시:
    - https://search.naver.com/search.naver?query=검색어...
    """
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)

        query = ""
        if 'query' in query_params:
            query = query_params['query'][0]
        elif 'where' in query_params and query_params['where'][0] == 'nexearch' and 'sm' in query_params:
             pass

        if query:
            title = f"{query} : 네이버 통합검색"
            description = f"'{query}'의 네이버 검색 결과입니다."
        else:
            title = "네이버 검색"
            description = "네이버 검색 결과입니다."

        return {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": None,
            "favicon_url": "https://ssl.pstatic.net/sstatic/search/favicon/favicon_191118_pc.ico",
            "site_name": "Naver",
            "url": url,
            "content": ""
        }

    except Exception as e:
        logger.error(f"Failed to parse Naver Search URL: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
