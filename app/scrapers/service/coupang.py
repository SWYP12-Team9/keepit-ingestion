import logging
from typing import Dict, Any

from app.scrapers.utils.scrape_utils import generate_basic_metadata

logger = logging.getLogger(__name__)

def scrape_coupang(url: str) -> Dict[str, Any]:
    """
    쿠팡 상품 페이지 메타데이터 수집

    현재는 기본 메타데이터만 반환합니다.
    """
    logger.info(f"Coupang URL detected, returning basic metadata: {url}")
    return generate_basic_metadata(url)
