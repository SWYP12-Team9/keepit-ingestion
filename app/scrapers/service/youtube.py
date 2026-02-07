"""
YouTube 스크래퍼 모듈

YouTube 영상의 메타데이터와 자막을 추출하는 함수들을 제공합니다.
"""

import logging
import re
import yt_dlp
from typing import Optional, Dict, Any
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from app.scrapers.utils.scrape_utils import generate_basic_metadata
import requests
from bs4 import BeautifulSoup
from app.scrapers.service.web import extract_favicon, extract_meta_tags
from app.scrapers.utils.headers import get_browser_headers

logger = logging.getLogger(__name__)

def extract_video_id(url: str) -> Optional[str]:
    """
    YouTube URL에서 video_id를 추출합니다.

    Args:
        url: YouTube URL

    Returns:
        video_id 또는 None
    """
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def normalize_youtube_url(url: str) -> Optional[str]:
    """
    YouTube URL을 정규화하여 video_id만 포함하는 깨끗한 URL로 변환합니다.

    &list=, &index= 등의 불필요한 쿼리 파라미터를 제거합니다.

    Args:
        url: 원본 YouTube URL (쿼리 파라미터 포함 가능)

    Returns:
        정규화된 YouTube URL (https://www.youtube.com/watch?v={video_id})
        또는 None (유효하지 않은 URL인 경우)

    Examples:
        >>> normalize_youtube_url("https://www.youtube.com/watch?v=h0KIWaUEIgQ&list=RDE4PftmmjVLI&index=2")
        "https://www.youtube.com/watch?v=h0KIWaUEIgQ"

        >>> normalize_youtube_url("https://youtu.be/h0KIWaUEIgQ")
        "https://www.youtube.com/watch?v=h0KIWaUEIgQ"
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None

    # 표준 YouTube URL 형식으로 재구성
    return f"https://www.youtube.com/watch?v={video_id}"


def get_transcript(video_id: str, languages: list = None) -> Optional[str]:
    """
    YouTube 자막을 추출합니다.

    Args:
        video_id: YouTube 비디오 ID
        languages: 선호하는 언어 리스트 (기본값: ['ko', 'en'])

    Returns:
        자막 텍스트 또는 에러 메시지
    """
    if languages is None:
        languages = ['ko', 'en']

    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=languages)
        return " ".join([t.text for t in transcript])
    except TranscriptsDisabled:
        return "이 영상은 자막 기능이 비활성화되어 있습니다."
    except NoTranscriptFound:
        return "해당 언어의 자막이 존재하지 않습니다."
    except Exception as e:
        return f"자막 추출 실패: {str(e)}"


def get_best_thumbnail(info: Dict[str, Any]) -> Optional[str]:
    """
    영상 정보에서 최고 해상도의 썸네일 URL을 추출합니다.

    Args:
        info: yt_dlp에서 추출한 영상 정보

    Returns:
        썸네일 URL 또는 None
    """
    if info.get("thumbnails"):
        thumbnails = sorted(
            info["thumbnails"],
            key=lambda x: x.get("width", 0) * x.get("height", 0),
            reverse=True
        )
        return thumbnails[0].get("url") if thumbnails else None
    elif info.get("thumbnail"):
        return info["thumbnail"]
    return None


def get_channel_icon(info: Dict[str, Any]) -> Optional[str]:
    """
    채널 아이콘 URL을 추출합니다.

    Args:
        info: yt_dlp에서 추출한 영상 정보

    Returns:
        채널 아이콘 URL 또는 None
    """
    # channel_thumbnails에서 추출 (yt_dlp가 제공하는 경우)
    if info.get("channel_thumbnails"):
        thumbnails = info["channel_thumbnails"]
        if isinstance(thumbnails, list) and len(thumbnails) > 0:
            # 가장 높은 해상도 선택
            best = max(thumbnails, key=lambda x: x.get("width", 0) * x.get("height", 0))
            return best.get("url")
        elif isinstance(thumbnails, dict):
            return thumbnails.get("url")

    # uploader_thumbnails에서 추출
    if info.get("uploader_thumbnails"):
        thumbnails = info["uploader_thumbnails"]
        if isinstance(thumbnails, list) and len(thumbnails) > 0:
            best = max(thumbnails, key=lambda x: x.get("width", 0) * x.get("height", 0))
            return best.get("url")

    # channel_url이 있다면 기본 아이콘 URL 구성
    if info.get("channel_id"):
        # YouTube 채널 아이콘의 기본 URL 패턴
        return f"https://yt3.ggpht.com/ytc/{info['channel_id']}"

    return None


def scrape_youtube(url: str, include_content: bool = True) -> Dict[str, Any]:
    """
    YouTube URL에서 메타데이터를 추출합니다.

    Args:
        url: YouTube URL
        include_content: 자막 포함 여부 (기본값: True)

    Returns:
        dict: {
            "success": bool,
            "title": str,
            "description": str,
            "image": str (영상 썸네일),
            "icon_url": str (채널 아이콘),
            "site_name": str,
            "url": str,
            "video_id": str,
            "transcript": str (optional),
            "duration": int,
            "view_count": int,
            "author": str,
        }
    """
    try:
        # URL 정규화 (&list, &index 등 제거)
        normalized_url = normalize_youtube_url(url)
        
        # 비디오 ID가 없으면(검색 페이지 등) 일반 웹 스크래퍼 로직 사용
        if not normalized_url:
             headers = get_browser_headers()
             
             # 리다이렉트를 명시적으로 허용
             response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
             if response.status_code == 200:
                 final_url = response.url
                 soup = BeautifulSoup(response.content, 'lxml')
                 metadata = extract_meta_tags(soup, final_url)

                 return {
                     "success": True,
                     "title": metadata["title"] or "YouTube",
                     "description": metadata["description"],
                     "thumbnail_url": metadata["thumbnail_url"],
                     "favicon_url": metadata["icon"],
                     "site_name": "YouTube",
                     "url": final_url,  # 리다이렉트 후 최종 URL
                 }
             else:
                 logger.warning(f"Failed to fetch YouTube page: {response.status_code}. Using basic metadata.")
                 return generate_basic_metadata(url)

        # video_id 추출
        video_id = extract_video_id(normalized_url)

        # yt_dlp로 기본 정보 추출 (정규화된 URL 사용)
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
            # 'cookiefile': 'cookies.txt', # 쿠키 파일이 있다면 사용
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(normalized_url, download=False)

        # 썸네일 추출 (주석 처리)
        # thumbnail = get_best_thumbnail(info)

        # 채널 아이콘 추출 (주석 처리)
        # channel_icon = get_channel_icon(info)

        # pytubefix로 추가 정보 추출 (선택적, 실패해도 계속 진행)
        try:
            yt = YouTube(normalized_url)
            title = yt.title or info.get("title")
            description = yt.description or info.get("description")
        except:
            title = info.get("title")
            description = info.get("description")

        # 일반 웹 스크래퍼 로직으로 아이콘(파비콘) 추출
        icon_url = None
        try:
            # requests import 이미 상단에 있음
            # headers import 수정됨
            
            headers = get_browser_headers()
            # 가볍게 요청 (타임아웃 짧게, 리다이렉트 허용)
            response = requests.get(normalized_url, headers=headers, timeout=5, allow_redirects=True)
            if response.status_code == 200:
                final_url = response.url
                soup = BeautifulSoup(response.content, 'lxml')
                icon_url = extract_favicon(soup, final_url)
        except Exception:
            pass # 아이콘 추출 실패 시 무시

        # 결과 딕셔너리 생성 (정규화된 URL 사용)
        thumbnail = get_best_thumbnail(info)
        result = {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail,
            "favicon_url": icon_url,
            "site_name": "YouTube",
            "url": normalized_url,
            # "video_id": video_id,
            # "duration": info.get("duration"),
            # "view_count": info.get("view_count"),
            # "author": info.get("uploader"),
        }

        # 자막 추출 (옵션)
        if include_content:
            transcript = get_transcript(video_id)
            if transcript:
                result["content"] = transcript

        return result

    except Exception as e:
        logger.error(f"YouTube scrape failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
