from .web_service import scrape_web
from .youtube_service import (
    scrape_youtube,
    extract_video_id,
    get_transcript,
    get_channel_icon,
    normalize_youtube_url,
)
from .instagram_service import scrape_instagram
from .google_service import scrape_google_search
from .coupang_service import scrape_coupang
from .naver_service import scrape_naver_map, scrape_naver_search, scrape_naver_blog
from .daum_service import scrape_daum_search
