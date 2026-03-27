"""
YouTube 스크래퍼 모듈

YouTube 영상의 메타데이터와 자막을 추출하는 함수들을 제공합니다.
메타데이터: YouTube Data API v3 (1순위) → pytubefix (2순위) → basic metadata (최종)
자막: youtube-transcript-api (기존 유지)
"""

import asyncio
import logging
import re
from pytubefix import YouTube
from typing import Optional, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from app.scrapers.dto.scrape_response import ScrapeResponse
from app.scrapers.utils.scrape_utils import generate_basic_metadata
import httpx
import os
from bs4 import BeautifulSoup
from app.scrapers.service.strategy.static_strategy import (
    extract_favicon,
    extract_meta_tags,
)
from app.scrapers.utils.headers import get_browser_headers

logger = logging.getLogger(__name__)

# YouTube Data API v3 설정
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")


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
        api = YouTubeTranscriptApi()
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


def _get_metadata_via_api(video_id: str) -> Optional[Dict[str, Any]]:
    """
    YouTube Data API v3로 메타데이터를 가져옵니다. (동기 함수)

    Returns:
        성공 시 dict(title, description, thumbnail_url, channel_title), 실패 시 None
    """
    api_key = YOUTUBE_API_KEY or os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not set, skipping YouTube Data API")
        return None

    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        youtube = build("youtube", "v3", developerKey=api_key)
        request = youtube.videos().list(
            part="snippet",
            id=video_id
        )
        response = request.execute()

        items = response.get("items", [])
        if not items:
            logger.warning(f"YouTube Data API: video not found - {video_id}")
            return None

        snippet = items[0]["snippet"]

        # 최고 해상도 썸네일 선택
        thumbnails = snippet.get("thumbnails", {})
        thumbnail_url = None
        for quality in ["maxres", "standard", "high", "medium", "default"]:
            if quality in thumbnails:
                thumbnail_url = thumbnails[quality].get("url")
                break

        return {
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "thumbnail_url": thumbnail_url,
            "channel_title": snippet.get("channelTitle"),
        }

    except Exception as e:
        error_str = str(e)
        if "quotaExceeded" in error_str or "rateLimitExceeded" in error_str:
            logger.warning(f"YouTube Data API quota exceeded: {e}")
        else:
            logger.warning(f"YouTube Data API failed: {e}")
        return None


def _get_metadata_via_pytubefix(normalized_url: str) -> Optional[Dict[str, Any]]:
    """
    pytubefix로 메타데이터를 가져옵니다. (동기 함수 - 무쿠키 fallback용)

    Returns:
        성공 시 dict(title, description, thumbnail_url, channel_title), 실패 시 None
    """
    try:
        youtube = YouTube(normalized_url)

        return {
            "title": youtube.title,
            "description": youtube.description,
            "thumbnail_url": youtube.thumbnail_url,
            "channel_title": youtube.author,
        }
    except Exception as e:
        logger.warning(f"pytubefix metadata extraction failed: {e}")
        return None


async def scrape_youtube(url: str, include_content: bool = True) -> ScrapeResponse:
    """
    YouTube URL에서 메타데이터를 추출합니다.

    우선순위:
    1. YouTube Data API v3 (안정적, API Key 필요)
    2. pytubefix (무쿠키 fallback)
    3. basic metadata (최종 fallback)
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
                return ScrapeResponse(
                    success=True,
                    title=metadata["title"] or "YouTube",
                    description=metadata["description"],
                    thumbnail_url=metadata["thumbnail_url"],
                    favicon_url=metadata["icon"],
                    site_name="YouTube",
                    url=final_url,
                )
            else:
                logger.warning(f"Failed to fetch YouTube page: {response.status_code}. Using basic metadata.")
                return generate_basic_metadata(url)

        video_id = extract_video_id(normalized_url)

        # 1순위: YouTube Data API v3
        metadata = await asyncio.to_thread(_get_metadata_via_api, video_id)

        # 2순위: pytubefix fallback (API 실패 시)
        if metadata is None:
            logger.info("Falling back to pytubefix for metadata: %s", video_id)
            metadata = await asyncio.to_thread(_get_metadata_via_pytubefix, normalized_url)

        # 모든 메타데이터 추출 실패 시 basic metadata 반환
        if metadata is None:
            logger.warning(f"All metadata extraction failed for {video_id}. Using basic metadata.")
            result = generate_basic_metadata(url)
            result.site_name = "YouTube"
            # 자막은 시도
            if include_content:
                transcript = await asyncio.to_thread(get_transcript, video_id)
                if transcript:
                    result.content = transcript
            return result

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

        result = ScrapeResponse(
            success=True,
            title=metadata["title"],
            description=metadata["description"],
            thumbnail_url=metadata["thumbnail_url"],
            favicon_url=icon_url,
            site_name="YouTube",
            url=normalized_url,
        )

        # 자막 추출 - 동기 함수 → to_thread로 실행
        if include_content:
            transcript = await asyncio.to_thread(get_transcript, video_id)
            if transcript:
                result.content = transcript

        return result

    except Exception as e:
        logger.error(f"YouTube scrape failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
