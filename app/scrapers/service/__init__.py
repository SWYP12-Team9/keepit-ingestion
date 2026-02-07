"""
스크래퍼 모듈

다양한 웹사이트에서 메타데이터를 추출하는 함수들을 제공합니다.
"""

from .youtube import scrape_youtube, extract_video_id, get_transcript, get_channel_icon, normalize_youtube_url
from .instagram import scrape_instagram
from .google import scrape_google_search
from .coupang import scrape_coupang
from .web import scrape_web, extract_meta_tags, extract_content, extract_favicon
from app.scrapers.utils.scrape_utils import (
    normalize_url,
    is_youtube_url,
    is_instagram_url,
    is_naver_blog_url,
    is_velog_url,
    is_tistory_url,
    is_google_search_url,
    is_coupang_url,
    detect_site_type,
    validate_url_safety,
    generate_basic_metadata
)

__all__ = [
    # YouTube functions
    "scrape_youtube",
    "extract_video_id",
    "get_transcript",
    "get_channel_icon",
    "normalize_youtube_url",

    # Instagram functions
    "scrape_instagram",

    # Google functions
    "scrape_google_search",

    # Coupang functions
    "scrape_coupang",

    # Web scraper functions
    "scrape_web",
    "extract_meta_tags",
    "extract_content",
    "extract_favicon",

    # Utility functions
    "normalize_url",
    "is_youtube_url",
    "is_instagram_url",
    "is_google_search_url",
    "is_naver_blog_url",
    "is_velog_url",
    "is_tistory_url",
    "is_coupang_url",
    "detect_site_type",
    "validate_url_safety",
    "generate_basic_metadata",
]
