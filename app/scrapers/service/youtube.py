"""
YouTube 스크래퍼 모듈

YouTube 영상의 메타데이터와 자막을 추출하는 함수들을 제공합니다.
"""

import asyncio
import logging
import re
import yt_dlp
from typing import Optional, Dict, Any
from pytubefix import YouTube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from app.scrapers.utils.scrape_utils import generate_basic_metadata
import httpx
import os
from bs4 import BeautifulSoup
from app.scrapers.service.web import extract_favicon, extract_meta_tags
from app.scrapers.utils.headers import get_browser_headers
import requests
from http.cookiejar import MozillaCookieJar

logger = logging.getLogger(__name__)

COOKIES_PATH = "/root/app/scraper/youtube_cookies.txt"

def extract_video_id(url: str) -> Optional[str]:
    """
    YouTube URL에서 video_id를 추출합니다.
    """
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    return match.group(1) if match else None


def normalize_youtube_url(url: str) -> Optional[str]:
    """
    YouTube URL을 정규화하여 video_id만 포함하는 깨끗한 URL로 변환합니다.
    """
    video_id = extract_video_id(url)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def get_transcript(video_id: str, languages: list = None) -> Optional[str]:
    """
    YouTube 자막을 추출합니다. (동기 함수 - asyncio.to_thread로 호출)
    """
    if languages is None:
        languages = ['ko', 'en']

    try:
        session = requests.Session()
        if os.path.exists(COOKIES_PATH):
            try:
                cj = MozillaCookieJar(COOKIES_PATH)
                cj.load(ignore_discard=True, ignore_expires=True)
                session.cookies.update(cj)
            except Exception as e:
                logger.warning(f"Failed to load youtube cookies: {e}")

        api = YouTubeTranscriptApi(http_client=session)
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(languages)
            fetched_transcript = transcript.fetch()
        except NoTranscriptFound:
            raise NoTranscriptFound(video_id, languages, transcript_list)

        texts = []
        for t in fetched_transcript:
            if hasattr(t, 'text'):
                texts.append(t.text)
            elif isinstance(t, dict) and 'text' in t:
                texts.append(t['text'])

        return " ".join(texts)
    except TranscriptsDisabled:
        logger.info("YouTube transcript disabled - video_id: %s", video_id)
        return None
    except NoTranscriptFound:
        logger.info("YouTube transcript not found - video_id: %s", video_id)
        return None
    except Exception as e:
        logger.warning("YouTube transcript extraction failed - video_id: %s, error: %s", video_id, e)
        return None


def get_best_thumbnail(info: Dict[str, Any]) -> Optional[str]:
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
    if info.get("channel_thumbnails"):
        thumbnails = info["channel_thumbnails"]
        if isinstance(thumbnails, list) and len(thumbnails) > 0:
            best = max(thumbnails, key=lambda x: x.get("width", 0) * x.get("height", 0))
            return best.get("url")
        elif isinstance(thumbnails, dict):
            return thumbnails.get("url")

    if info.get("uploader_thumbnails"):
        thumbnails = info["uploader_thumbnails"]
        if isinstance(thumbnails, list) and len(thumbnails) > 0:
            best = max(thumbnails, key=lambda x: x.get("width", 0) * x.get("height", 0))
            return best.get("url")

    if info.get("channel_id"):
        return f"https://yt3.ggpht.com/ytc/{info['channel_id']}"

    return None


async def scrape_youtube(url: str, include_content: bool = True) -> Dict[str, Any]:
    """
    YouTube URL에서 메타데이터를 추출합니다.
    """
    try:
        normalized_url = normalize_youtube_url(url)

        # 비디오 ID가 없으면 일반 웹 스크래퍼 로직 사용
        if not normalized_url:
            headers = get_browser_headers()
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                final_url = str(response.url)
                soup = BeautifulSoup(response.content, 'lxml')
                metadata = await extract_meta_tags(soup, final_url)
                return {
                    "success": True,
                    "title": metadata["title"] or "YouTube",
                    "description": metadata["description"],
                    "thumbnail_url": metadata["thumbnail_url"],
                    "favicon_url": metadata["icon"],
                    "site_name": "YouTube",
                    "url": final_url,
                }
            else:
                logger.warning(f"Failed to fetch YouTube page: {response.status_code}. Using basic metadata.")
                return generate_basic_metadata(url)

        video_id = extract_video_id(normalized_url)

        # yt_dlp는 동기 블로킹 → to_thread로 실행
        ydl_opts = {'quiet': True, 'skip_download': True, 'no_warnings': True}
        def _extract_ydl_info():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(normalized_url, download=False)

        info = await asyncio.to_thread(_extract_ydl_info)

        # pytubefix도 동기 블로킹 → to_thread로 실행
        def _get_yt_details():
            try:
                yt = YouTube(normalized_url)
                return yt.title, yt.description
            except Exception:
                return None, None

        yt_title, yt_description = await asyncio.to_thread(_get_yt_details)
        title = yt_title or info.get("title")
        description = yt_description or info.get("description")

        # 파비콘 추출
        icon_url = None
        try:
            headers = get_browser_headers()
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(normalized_url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'lxml')
                icon_url = await extract_favicon(soup, str(response.url))
        except Exception:
            pass

        thumbnail = get_best_thumbnail(info)
        result = {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail,
            "favicon_url": icon_url,
            "site_name": "YouTube",
            "url": normalized_url,
        }

        # 자막 추출 - 동기 함수 → to_thread로 실행
        if include_content:
            transcript = await asyncio.to_thread(get_transcript, video_id)
            if transcript:
                result["content"] = transcript

        return result

    except Exception as e:
        logger.error(f"YouTube scrape failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
