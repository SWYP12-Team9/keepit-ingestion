"""
Daum 검색 핸들러 모듈

Daum 검색 URL에서 검색어를 추출하여 메타데이터를 생성합니다.
"""

import logging
from typing import Dict, Any
from urllib.parse import urlparse, parse_qs
from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)

def scrape_daum_search(url: str) -> Dict[str, Any]:
    """
    Daum 검색 URL에서 검색어를 추출합니다.
    
    URL 구조 예시:
    - https://search.daum.net/search?w=tot&DA=YZR&t__nil_searchbox=btn&q=강남+맛집
    """
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        query = ""
        if 'q' in query_params:
            query = query_params['q'][0]
            
        if query:
            title = f"{query} | Daum 검색"
            description = f"'{query}'의 Daum 검색 결과입니다."
        else:
            title = "Daum 검색"
            description = "Daum 검색 결과입니다."

        return {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": None,
            "favicon_url": "https://search.daum.net/favicon.ico",
            "site_name": "Daum",
            "url": url,
            "content": ""
        }
            
    except Exception as e:
        logger.error(f"Failed to parse Daum Search URL: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
