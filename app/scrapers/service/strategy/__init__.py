"""
스크래핑 전략 패키지

정적(Static) 및 동적(Dynamic) 스크래핑 엔진 구현체를 포함합니다.
"""

from .dynamic_strategy import scrape_dynamic
from .static_strategy import scrape_static

__all__ = ["scrape_dynamic", "scrape_static"]
