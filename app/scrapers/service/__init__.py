"""
스크래퍼 서비스 패키지

기능별 서브패키지로 구성됩니다:
- strategy/: 정적/동적 스크래핑 전략
- provider/: Playwright, Apify 같은 외부 구현체
- platform/: 기본 웹 처리와 특정 사이트 전용 스크래핑 서비스
"""

from .scrape_orchestrator import scrape_url
from .platform.youtube_service import (
    scrape_youtube,
    extract_video_id,
    get_transcript,
    get_channel_icon,
    normalize_youtube_url,
)
from .platform.instagram_service import scrape_instagram
from .platform.google_service import scrape_google_search
from .platform.coupang_service import scrape_coupang
from .platform.naver_service import scrape_naver_map, scrape_naver_search
from .platform.daum_service import scrape_daum_search
from .strategy.static_strategy import (
    scrape_static,
    extract_meta_tags,
    extract_content,
    extract_favicon,
)
from .strategy.dynamic_strategy import scrape_dynamic
from .platform.web_service import scrape_web

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
    # External orchestrator
    "scrape_url",

    # Static & Dynamic Strategies
    "scrape_static",
    "scrape_dynamic",

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
