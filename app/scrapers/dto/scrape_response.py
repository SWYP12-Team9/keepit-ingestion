"""
스크래핑 결과 DTO

모든 스크래퍼가 공통으로 반환하는 결과 객체입니다.
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class ScrapeResponse:
    """스크래핑 결과를 담는 공통 DTO"""
    success: bool = True
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    favicon_url: Optional[str] = None
    site_name: Optional[str] = None
    url: str = ""
    content: Optional[str] = None
    error: Optional[str] = None
    # 내부 오케스트레이션용 플래그: API 응답에는 포함하지 않음
    force_dynamic_render: bool = False
    dynamic_render_reason: Optional[str] = None

    def to_dict(self) -> dict:
        """API 응답용 dict 변환. None인 필드도 포함하여 기존 호환성 유지."""
        result = asdict(self)
        del result["force_dynamic_render"]
        del result["dynamic_render_reason"]
        # error 필드가 None이면 제거 (정상 응답에는 불필요)
        if result.get("error") is None:
            del result["error"]
        # content가 None이면 제거 (선택적 필드)
        if result.get("content") is None:
            del result["content"]
        return result
