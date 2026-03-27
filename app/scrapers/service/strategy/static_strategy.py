"""
정적 웹사이트 스크래핑 전략 모듈

httpx와 BeautifulSoup을 사용하여 JS 렌더링 없이 
HTML 소스에서 직접 메타데이터와 본문을 추출합니다.
"""

import json
import logging
import re
import httpx
import trafilatura
from bs4 import BeautifulSoup, Comment
from urllib.parse import urljoin, urlparse
from typing import Dict, Any, Optional

from app.scrapers.utils.headers import get_browser_headers
from app.scrapers.dto.scrape_response import ScrapeResponse

logger = logging.getLogger(__name__)

MIN_CONTENT_LENGTH = 100

BOILERPLATE_TAGS = (
    "script",
    "style",
    "noscript",
    "nav",
    "footer",
    "aside",
    "form",
)

BOILERPLATE_ROLES = {
    "banner",
    "complementary",
    "contentinfo",
    "navigation",
    "search",
}

STRUCTURED_CONTENT_KEYS = (
    "articleBody",
    "content",
    "description",
    "headline",
    "text",
)

HYDRATION_MARKERS = (
    "__APOLLO_STATE__",
    "__INITIAL_STATE__",
    "__NEXT_DATA__",
    "__NUXT__",
    "apollo-state",
    "hydration",
)

SPA_ROOT_SELECTORS = (
    "#__next",
    "#__nuxt",
    "#root",
    "#app",
    "#app-root",
    "[data-reactroot]",
    "[ng-version]",
)

LOADING_TEXT_MARKERS = (
    "loading",
    "불러오는 중",
    "로딩 중",
    "잠시만 기다려주세요",
    "please wait",
)

LOADING_SELECTORS = (
    "[aria-busy='true']",
    "[role='progressbar']",
    "[class*='loading']",
    "[class*='skeleton']",
    "[class*='placeholder']",
)


def _is_boilerplate_block(tag: Any) -> bool:
    if not getattr(tag, "name", None):
        return False

    if tag.name in BOILERPLATE_TAGS:
        return True

    role = str(tag.get("role", "")).strip().lower()
    if role in BOILERPLATE_ROLES:
        return True

    return False


def sanitize_content_html(html: str) -> str:
    """본문 추출 전에 불필요한 UI/광고 영역을 제거합니다."""
    soup = BeautifulSoup(html, "html.parser")

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    for tag in soup.find_all(_is_boilerplate_block):
        tag.decompose()

    content_root = soup.body or soup
    return str(content_root)


def _normalize_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    normalized = re.sub(r"\s+", " ", value).strip()
    return normalized or None


def _truncate_text(content: str, max_length: int) -> str:
    return content[:max_length] if len(content) > max_length else content


def _is_sufficient_content(content: Optional[str], min_length: int = MIN_CONTENT_LENGTH) -> bool:
    return bool(content and len(content.strip()) >= min_length)


def _append_unique_text(bucket: list[str], value: Optional[str]) -> None:
    if not value:
        return
    if value not in bucket:
        bucket.append(value)


def _collect_structured_content(payload: Any, collected: dict[str, list[str]]) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in STRUCTURED_CONTENT_KEYS:
                _append_unique_text(collected[key], _normalize_text(value))
            _collect_structured_content(value, collected)
        return

    if isinstance(payload, list):
        for item in payload:
            _collect_structured_content(item, collected)


def _extract_json_ld_content(soup: BeautifulSoup) -> Optional[str]:
    collected = {key: [] for key in STRUCTURED_CONTENT_KEYS}

    for script in soup.find_all("script"):
        script_type = str(script.get("type", "")).lower()
        if "ld+json" not in script_type:
            continue

        raw_text = script.string or script.get_text()
        if not raw_text or not raw_text.strip():
            continue

        try:
            payload = json.loads(raw_text)
        except Exception:
            continue

        _collect_structured_content(payload, collected)

    return _build_structured_content(collected)


def _extract_hydration_content(soup: BeautifulSoup) -> Optional[str]:
    collected = {key: [] for key in STRUCTURED_CONTENT_KEYS}
    field_pattern = re.compile(
        r'"(?P<key>articleBody|content|description|headline|text)"\s*:\s*"(?P<value>(?:\\.|[^"\\])*)"',
        re.DOTALL,
    )

    for script in soup.find_all("script"):
        raw_text = script.string or script.get_text()
        if not raw_text:
            continue

        marker_text = " ".join(
            filter(
                None,
                [
                    raw_text,
                    str(script.get("id", "")),
                    str(script.get("type", "")),
                ],
            )
        )
        if not any(marker in marker_text for marker in HYDRATION_MARKERS):
            continue

        for match in field_pattern.finditer(raw_text):
            key = match.group("key")
            try:
                value = json.loads(f'"{match.group("value")}"')
            except json.JSONDecodeError:
                continue
            _append_unique_text(collected[key], _normalize_text(value))

    return _build_structured_content(collected)


def _build_structured_content(collected: dict[str, list[str]]) -> Optional[str]:
    ordered_keys = ("headline", "description", "articleBody", "content", "text")
    merged: list[str] = []

    for key in ordered_keys:
        for value in collected[key]:
            _append_unique_text(merged, value)

    if not merged:
        return None

    return "\n\n".join(merged)


def _extract_dom_content(html: str) -> Optional[str]:
    sanitized_html = sanitize_content_html(html)
    return trafilatura.extract(sanitized_html, include_comments=False)


def should_force_dynamic_render(
    html: str,
    content: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """
    정적 HTML 구조만으로 JS 렌더링 필요성이 강한 경우를 판별합니다.
    """
    dom_content = content if content is not None else _extract_dom_content(html)
    soup = BeautifulSoup(html, "html.parser")

    body = soup.body or soup
    visible_text = _normalize_text(body.get_text(" ", strip=True)) or ""
    article_like = soup.select_one("article, main, [role='main']")
    article_text = ""
    if article_like:
        article_text = _normalize_text(article_like.get_text(" ", strip=True)) or ""

    has_spa_root = any(soup.select_one(selector) is not None for selector in SPA_ROOT_SELECTORS)
    has_loading_ui = any(soup.select_one(selector) is not None for selector in LOADING_SELECTORS)
    has_loading_text = any(marker in visible_text.lower() for marker in LOADING_TEXT_MARKERS)

    hydration_payload_sizes = []
    hydration_scripts = 0
    for script in soup.find_all("script"):
        raw_text = script.string or script.get_text()
        if not raw_text:
            continue
        marker_text = " ".join(
            filter(
                None,
                [
                    raw_text,
                    str(script.get("id", "")),
                    str(script.get("type", "")),
                ],
            )
        )
        if any(marker in marker_text for marker in HYDRATION_MARKERS):
            hydration_scripts += 1
            hydration_payload_sizes.append(len(raw_text))

    max_hydration_size = max(hydration_payload_sizes, default=0)
    dom_is_weak = not _is_sufficient_content(dom_content)
    article_is_sparse = bool(article_like) and len(article_text) < MIN_CONTENT_LENGTH
    visible_text_is_sparse = len(visible_text) < 300

    if dom_is_weak and has_loading_ui:
        return True, "loading-ui"

    if dom_is_weak and has_loading_text:
        return True, "loading-text"

    if dom_is_weak and has_spa_root and hydration_scripts > 0:
        return True, "spa-root-with-hydration"

    if dom_is_weak and max_hydration_size >= 2000 and visible_text_is_sparse:
        return True, "large-hydration-payload"

    if article_is_sparse and has_spa_root and hydration_scripts > 0:
        return True, "sparse-article-shell"

    return False, None

async def extract_favicon(soup: BeautifulSoup, url: str) -> Optional[str]:
    """HTML에서 favicon/icon을 추출합니다."""
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

    # 4. 기본 favicon.ico 경로
    try:
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
    """HTML에서 메타 태그를 추출합니다."""
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

def extract_content(
    html: str,
    max_length: int = 500,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> Optional[str]:
    """HTML에서 본문 내용을 추출합니다."""
    dom_content = _extract_dom_content(html)
    if _is_sufficient_content(dom_content):
        return _truncate_text(dom_content, max_length)

    soup = BeautifulSoup(html, "html.parser")

    structured_content = _extract_json_ld_content(soup)
    if not _is_sufficient_content(structured_content):
        structured_content = _extract_hydration_content(soup)
    if structured_content:
        return _truncate_text(structured_content, max_length)

    if dom_content:
        return _truncate_text(dom_content, max_length)

    return None

async def scrape_static(url: str, include_content: bool = True, max_length: int = 1000) -> ScrapeResponse:
    """HTTP 클라이언트를 사용하여 정적으로 웹페이지를 스크래핑합니다."""
    headers = get_browser_headers()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=headers, timeout=10)
        response.raise_for_status()

    final_url = str(response.url)
    soup = BeautifulSoup(response.content, 'html.parser')
    metadata = await extract_meta_tags(soup, final_url)

    result = ScrapeResponse(
        success=True,
        title=metadata["title"],
        description=metadata["description"],
        thumbnail_url=metadata["thumbnail_url"],
        favicon_url=metadata["icon"],
        site_name=metadata["site_name"],
        url=final_url,
    )

    if include_content:
        content = extract_content(
            response.text,
            max_length=max_length,
            title=metadata["title"],
            description=metadata["description"],
        )
        if content:
            result.content = content
        else:
            # iframe 팔로우 로직
            iframe_tag = soup.select_one("iframe#mainFrame, frame#mainFrame, iframe[name='mainFrame'], frame[name='mainFrame']")
            if iframe_tag and iframe_tag.get("src"):
                iframe_src = iframe_tag.get("src")
                iframe_url = urljoin(final_url, iframe_src)
                try:
                    async with httpx.AsyncClient(follow_redirects=True) as client:
                        iframe_response = await client.get(iframe_url, headers=headers, timeout=10)
                        if iframe_response.status_code == 200:
                            iframe_content = extract_content(iframe_response.text, max_length=max_length)
                            if iframe_content:
                                result.content = iframe_content
                except Exception:
                    pass

    force_dynamic_render, dynamic_render_reason = should_force_dynamic_render(
        response.text,
        result.content,
    )
    result.force_dynamic_render = force_dynamic_render
    result.dynamic_render_reason = dynamic_render_reason
    
    return result
