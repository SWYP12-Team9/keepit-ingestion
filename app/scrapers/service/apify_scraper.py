"""
Apify Fallback 스크래퍼 모듈

모든 스크래핑 시도가 실패했을 때 최후의 수단으로 Apify Actor를 사용합니다.
"""

import os
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
from apify_client import ApifyClient
from app.scrapers.utils.scrape_utils import generate_basic_metadata
from .web import extract_meta_tags

logger = logging.getLogger(__name__)

def scrape_with_apify(url: str) -> Optional[Dict[str, Any]]:
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
        client = ApifyClient(api_token)

        # Puppeteer Scraper 설정
        run_input = {
            "startUrls": [{"url": url}],
            # 페이지 로딩 후 HTML 추출
            "pageFunction": """async function pageFunction(context) {
                const { page, request, log } = context;
                
                // 페이지 안정화 대기
                try {
                    await page.waitForLoadState('networkidle', { timeout: 10000 });
                } catch (e) {
                    log.warning('Network idle timeout, proceeding anyway');
                }
                
                const html = await page.content();
                return { 
                    html, 
                    url: request.url 
                };
            }""",
            "useChrome": True,
            "stealth": True,
        }

        # Actor 실행 (apify/puppeteer-scraper)
        run = client.actor("apify/puppeteer-scraper").call(run_input=run_input)
        
        if not run:
             logger.error("Apify actor run failed to start.")
             return None

        # 결과 가져오기
        dataset = client.dataset(run["defaultDatasetId"])
        items = dataset.list_items().items
        if not items:
            logger.warning("Apify returned no items.")
            return None

        item = items[0]
        html = item.get("html")
        
        # web.py와 동일한 로직으로 메타데이터 추출 시도
        if html:
            soup = BeautifulSoup(html, "html.parser")
            metadata = extract_meta_tags(soup, item.get("url", url))
            
            title = metadata["title"]
            description = metadata["description"]
            thumbnail_url = metadata["thumbnail_url"]
            favicon_url = metadata["icon"]
            site_name = metadata["site_name"]
            
            # description이 비어있으면 html에서 직접 다시 찾기 시도 (BeautifulSoup 이슈 대비)
            if not description:
                desc_tag = soup.find("meta", attrs={"name": "description"})
                if desc_tag:
                    description = desc_tag.get("content")
            
        else:
            logger.warning("Apify returned no HTML content.")
            return None

        # Site Name이 없으면 도메인에서 추출 시도 (공통)
        if not site_name:
             # 도메인에서 추출 시도
             from urllib.parse import urlparse
             try:
                 site_name = urlparse(url).netloc
             except:
                 pass

        return {
            "success": True,
            "title": title,
            "description": description,
            "thumbnail_url": thumbnail_url,
            "favicon_url": favicon_url,
            "site_name": site_name,
            "url": item.get("url", url),
            "content": None # Puppeteer는 본문 추출 안 함 (필요시 trafilatura 사용 가능)
        }

    except Exception as e:
        logger.error(f"Apify fallback failed: {str(e)}")
        return None
