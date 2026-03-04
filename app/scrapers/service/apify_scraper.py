"""
Apify Fallback 스크래퍼 모듈

모든 스크래핑 시도가 실패했을 때 최후의 수단으로 Apify Actor를 사용합니다.
"""

import asyncio
import os
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from apify_client import ApifyClient
from app.scrapers.utils.scrape_utils import generate_basic_metadata
from .web import extract_meta_tags

logger = logging.getLogger(__name__)

async def scrape_with_apify(url: str) -> Optional[Dict[str, Any]]:
    """
    Apify Actor를 사용하여 웹페이지를 스크래핑합니다.
    'apify/website-content-crawler' Actor를 사용합니다.

    Args:
        url: 스크래핑할 URL

    Returns:
        성공 시 메타데이터 딕셔너리, 실패 시 None
    """
    api_token = os.environ.get("APIFY_API_KEY")
    if not api_token:
        logger.warning("APIFY_API_KEY not set. Skipping Apify fallback.")
        return None

    try:
        logger.info(f"Attempting Apify fallback for: {url}")

        run_input = {
            "startUrls": [{"url": url}],
            "pageFunction": """async function pageFunction(context) {
                const { page, request, log } = context;
                try {
                    await page.waitForLoadState('networkidle', { timeout: 10000 });
                } catch (e) {
                    log.warning('Network idle timeout, proceeding anyway');
                }
                const html = await page.content();
                return { html, url: request.url };
            }""",
            "useChrome": True,
            "stealth": True,
        }

        # ApifyClient는 동기 라이브러리 → to_thread로 실행
        def _run_apify():
            client = ApifyClient(api_token)
            run = client.actor("apify/puppeteer-scraper").call(run_input=run_input)
            if not run:
                return None
            dataset = client.dataset(run["defaultDatasetId"])
            return dataset.list_items().items

        items = await asyncio.to_thread(_run_apify)

        if not items:
            logger.warning("Apify returned no items.")
            return None

        item = items[0]
        html = item.get("html")

        if not html:
            logger.warning("Apify returned no HTML content.")
            return None

        soup = BeautifulSoup(html, "html.parser")
        metadata = await extract_meta_tags(soup, item.get("url", url))

        title = metadata["title"]
        description = metadata["description"]
        thumbnail_url = metadata["thumbnail_url"]
        favicon_url = metadata["icon"]
        site_name = metadata["site_name"]

        if not description:
            desc_tag = soup.find("meta", attrs={"name": "description"})
            if desc_tag:
                description = desc_tag.get("content")

        if not site_name:
            from urllib.parse import urlparse
            try:
                site_name = urlparse(url).netloc
            except Exception:
                pass

        return {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "favicon_url": favicon_url,
            "site_name": site_name,
            "url": item.get("url", url),
            "content": None
        }

    except Exception as e:
        logger.error(f"Apify fallback failed: {str(e)}")
        return None
