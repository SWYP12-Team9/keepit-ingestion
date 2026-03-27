"""
Google 검색 결과 핸들러 모듈

Google 검색 URL에서 검색어를 추출하여 메타데이터를 반환합니다.
"""

import logging
from urllib.parse import urlparse, parse_qs
from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)

def scrape_google_search(url: str) -> ScrapeResponse:
    """
    Google 검색 URL에서 검색어를 추출하고 메타데이터를 생성합니다.

    Args:
        url: Google 검색 URL

    Returns:
        ScrapeResponse
    """
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # 'q' 파라미터 추출
        search_query = ""
        if 'q' in query_params:
            search_query = query_params['q'][0]
        
        if not search_query:
            title = "Google"
            description = "Google"
        else:
            title = f"{search_query} | Google 검색"
            description = f"'{search_query}'의 Google 검색 결과입니다."

        return ScrapeResponse(
            success=True,
            title=title,
            description=description,
            thumbnail_url=None,
            favicon_url="https://www.google.com/favicon.ico",
            site_name="Google",
            url=url,
            content="",
        )
    except Exception as e:
        logger.error(f"Failed to parse Google search URL: {str(e)}. Using basic basic_metadata.")
        return generate_basic_metadata(url)