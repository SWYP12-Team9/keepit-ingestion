"""
일반 웹사이트 스크래퍼 모듈

Open Graph, Twitter Card 등의 메타 태그를 추출하고
본문 내용을 파싱하는 함수들을 제공합니다.
"""

import logging
import trafilatura
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any
from app.scrapers.utils.headers import get_browser_headers
from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)


async def extract_favicon(soup: BeautifulSoup, url: str) -> str:
    """
    HTML에서 favicon/icon을 추출합니다.

    Args:
        soup: BeautifulSoup 객체
        url: 원본 URL

    Returns:
        favicon URL 또는 None
    """
    # 1. 일반 icon
    icon_tag = soup.find("link", rel=lambda x: x and 'icon' in (x if isinstance(x, list) else x.split()))
    if icon_tag and icon_tag.get("href"):
        icon_url = icon_tag["href"]
        if not icon_url.startswith("http"):
            icon_url = urljoin(url, icon_url)
        return icon_url

    # 2. shortcut icon
    shortcut_icon = soup.find("link", rel="shortcut icon")
    if shortcut_icon and shortcut_icon.get("href"):
        icon_url = shortcut_icon["href"]
        if not icon_url.startswith("http"):
            icon_url = urljoin(url, icon_url)
        return icon_url

    # 3. Apple touch icon
    apple_icon = soup.find("link", rel=lambda x: x and 'apple-touch-icon' in (x if isinstance(x, list) else x.split()))
    if apple_icon and apple_icon.get("href"):
        icon_url = apple_icon["href"]
        if not icon_url.startswith("http"):
            icon_url = urljoin(url, icon_url)
        return icon_url

    # 4. 기본 favicon.ico 경로 HEAD 요청으로 확인
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        default_favicon = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.head(default_favicon, timeout=2)
            if response.status_code == 200:
                return default_favicon
    except Exception:
        pass

    return None


async def extract_meta_tags(soup: BeautifulSoup, url: str) -> Dict[str, Any]:
    """
    HTML에서 메타 태그를 추출합니다.
    Open Graph, Twitter Card, 일반 메타 태그를 지원합니다.

    Args:
        soup: BeautifulSoup 객체
        url: 원본 URL

    Returns:
        dict: {
            "title": str,
            "description": str,
            "thumbnail_url": str,
            "icon": str,
            "site_name": str,
            "url": str,
        }
    """
    metadata = {
        "title": None,
        "description": None,
        "thumbnail_url": None,
        "icon": None,
        "site_name": None,
        "url": url,
    }

    og_title = soup.find("meta", property="og:title")
    og_description = soup.find("meta", property="og:description")
    og_image = soup.find("meta", property="og:image")
    og_site_name = soup.find("meta", property="og:site_name")

    twitter_title = soup.find("meta", attrs={"name": "twitter:title"})
    twitter_description = soup.find("meta", attrs={"name": "twitter:description"})
    twitter_image = soup.find("meta", attrs={"name": "twitter:image"})

    meta_description = soup.find("meta", attrs={"name": "description"})

    if og_title and og_title.get("content"):
        metadata["title"] = og_title["content"]
    elif twitter_title and twitter_title.get("content"):
        metadata["title"] = twitter_title["content"]
    elif soup.title and soup.title.string:
        metadata["title"] = soup.title.string.strip()

    if og_description and og_description.get("content"):
        metadata["description"] = og_description["content"]
    elif twitter_description and twitter_description.get("content"):
        metadata["description"] = twitter_description["content"]
    elif meta_description and meta_description.get("content"):
        metadata["description"] = meta_description["content"]

    if og_image and og_image.get("content"):
        metadata["thumbnail_url"] = og_image["content"]
    elif twitter_image and twitter_image.get("content"):
        metadata["thumbnail_url"] = twitter_image["content"]

    if metadata["thumbnail_url"] and not metadata["thumbnail_url"].startswith("http"):
        metadata["thumbnail_url"] = urljoin(url, metadata["thumbnail_url"])

    metadata["icon"] = await extract_favicon(soup, url)

    if og_site_name and og_site_name.get("content"):
        metadata["site_name"] = og_site_name["content"]

    return metadata


def extract_content(html: str, max_length: int = 500) -> str:
    """
    HTML에서 본문 내용을 추출합니다.

    Args:
        html: HTML 문자열
        max_length: 최대 길이 (기본값: 500자)

    Returns:
        본문 내용 (최대 max_length자)
    """
    content = trafilatura.extract(html, include_comments=False)
    if content:
        return content[:max_length] if len(content) > max_length else content
    return None


async def scrape_web(url: str, include_content: bool = True, max_length: int = 1000) -> Dict[str, Any]:
    """
    일반 웹페이지에서 메타데이터를 추출합니다.

    Args:
        url: 웹페이지 URL
        include_content: 본문 내용 포함 여부 (기본값: True)
        max_length: 본문 미리보기 최대 길이 (기본값: 1000)

    Returns:
        dict: {
            "success": bool,
            "title": str,
            "description": str,
            "thumbnail_url": str,
            "favicon_url": str,
            "site_name": str,
            "url": str,
            "content": str (optional),
        }
    """
    try:
        headers = get_browser_headers()
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()

        final_url = str(response.url)
        soup = BeautifulSoup(response.content, 'html.parser')
        metadata = await extract_meta_tags(soup, final_url)

        result = {
            "success": True,
            "title": metadata["title"],
            "description": metadata["description"],
            "thumbnail_url": metadata["thumbnail_url"],
            "favicon_url": metadata["icon"],
            "site_name": metadata["site_name"],
            "url": final_url,
        }

        if include_content:
            content = extract_content(response.text, max_length=max_length)
            if content:
                result["content"] = content
            else:
                iframe_tag = soup.select_one("iframe#mainFrame, frame#mainFrame, iframe[name='mainFrame'], frame[name='mainFrame']")
                if iframe_tag and iframe_tag.get("src"):
                    iframe_src = iframe_tag.get("src")
                    iframe_url = urljoin(final_url, iframe_src)
                    logger.info(f"Content extraction initial failed. Attempting to follow iframe: {iframe_url}")
                    try:
                        async with httpx.AsyncClient(follow_redirects=True) as client:
                            iframe_response = await client.get(iframe_url, headers=headers, timeout=10)
                            if iframe_response.status_code == 200:
                                iframe_content = extract_content(iframe_response.text, max_length=max_length)
                                if iframe_content:
                                    result["content"] = iframe_content
                                    logger.info("Successfully extracted content from iframe.")
                    except Exception as e:
                        logger.warning(f"Failed to extract content from iframe: {str(e)}")

        return result

    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.warning(f"Generic web scraping failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
    except Exception as e:
        logger.error(f"Generic web parsing failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
