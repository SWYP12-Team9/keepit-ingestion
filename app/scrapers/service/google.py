"""
Google 검색 결과 핸들러 모듈

Google 검색 URL에서 검색어를 추출하여 메타데이터를 반환합니다.
"""

import logging
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs, unquote
from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)

def scrape_google_search(url: str) -> Dict[str, Any]:
    """
    Google 검색 URL에서 검색어를 추출하고 메타데이터를 생성합니다.

    Args:
        url: Google 검색 URL

    Returns:
        dict: {
            "success": True,
            "title": str,
            "description": str,
            "thumbnail_url": None,
            "favicon_url": "https://www.google.com/favicon.ico",
            "site_name": "Google",
            "url": str,
            "content": ""
        }
    """
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # 'q' 파라미터 추출
        search_query = ""
        if 'q' in query_params:
            search_query = query_params['q'][0]
        
        # 검색어 디코딩 (이미 parse_qs에서 어느 정도 처리되지만 보수적으로 검색어만 깔끔하게 처리)
        # title: "[검색어] : Google 검색"
        # description: "'[검색어]'의 Google 검색 결과입니다."
        
        if not search_query:
            # 검색어가 없을 경우 (예: google.com 메인)
            title = "Google"
            description = "Google"
        else:
            title = f"{search_query} | Google 검색"
            description = f"'{search_query}'의 Google 검색 결과입니다."

        return {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": None,
            "favicon_url": "https://www.google.com/favicon.ico",
            "site_name": "Google",
            "url": url,
            "content": ""
        }
    except Exception as e:
        logger.error(f"Failed to parse Google search URL: {str(e)}. Using basic basic_metadata.")
        return generate_basic_metadata(url)
    