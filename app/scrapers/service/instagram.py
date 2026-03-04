import asyncio
import os
import logging
from typing import Dict, Any
from apify_client import ApifyClient
from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)

async def scrape_instagram(url: str, max_length: int = 200) -> Dict[str, Any]:
    """
    Instagram URL에서 메타데이터를 추출 (Apify 사용).

    Apify의 'instagram-scraper' 행위자를 사용합니다.
    환경 변수 APIFY_API_KEY이 필요

    Args:
        url: Instagram URL (포스트, 릴스 등)

    Returns:
        dict: {
            "success": bool,
            "title": str,
            "description": str,
            "thumbnail_url": str,
            "favicon_url": str,
            "site_name": str,
            "url": str,
            "content": str (본문 + 댓글),
        }
    """
    api_token = os.environ.get("APIFY_API_KEY")
    if not api_token:
        logger.warning("APIFY_API_KEY environment variable is not set. Using basic metadata.")
        return generate_basic_metadata(url)

    try:
        run_input = {
            "directUrls": [url],
            "resultsType": "posts",
            "searchType": "hashtag",
            "searchLimit": 1,
            "addParentData": False,
        }

        # ApifyClient는 동기 라이브러리 → to_thread로 실행
        def _run_apify():
            client = ApifyClient(api_token)
            run = client.actor("shu8hvrXbJbY3Eb9W").call(run_input=run_input)
            dataset = client.dataset(run["defaultDatasetId"])
            return dataset.list_items().items

        items = await asyncio.to_thread(_run_apify)

        if not items:
            return generate_basic_metadata(url)

        post = items[0]

        caption = post.get("caption", "")
        image_url = post.get("displayUrl") or (post.get("images", [{}])[0].get("url") if post.get("images") else None)
        icon_url = "https://static.cdninstagram.com/rsrc.php/v3/yI/r/VsNE-OHk_8a.png"

        comments = post.get("latestComments", [])
        comments_text = "\n".join([f"{c.get('ownerUsername', 'User')}: {c.get('text', '')}" for c in comments])

        likes_count = post.get("likesCount", 0)
        comments_count = post.get("commentsCount", 0)

        content_parts = []
        if caption:
            content_parts.append(f"[Caption]\n{caption}")

        content_parts.append(f"\n[Stats]\nLikes: {likes_count}, Comments: {comments_count}")

        if comments_text:
            content_parts.append(f"\n[Comments]\n{comments_text}")

        full_content = "\n\n".join(content_parts)

        title = caption.split('\n')[0][:100] if caption else "Instagram Post"
        description = caption[:max_length] + "..." if caption and len(caption) > max_length else caption

        return {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": image_url,
            "favicon_url": icon_url,
            "site_name": "Instagram",
            "url": post.get("url", url),
            "content": full_content
        }

    except Exception as e:
        logger.error(f"Apify detailed scraping failed: {str(e)}. Using basic metadata.")
        return generate_basic_metadata(url)
