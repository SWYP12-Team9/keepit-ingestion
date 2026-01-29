from pydantic import BaseModel, Field
from typing import List, Optional

class URLRequest(BaseModel):
    url: str = Field(..., description="스크래핑할 URL")
    max_length: Optional[int] = Field(1000, description="본문 미리보기 최대 길이 (기본값: 1000)")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "max_length": 1000
            }
        }

class URLListRequest(BaseModel):
    urls: List[str] = Field(..., description="스크래핑할 URL 리스트", max_items=10)
    max_length: Optional[int] = Field(1000, description="본문 미리보기 최대 길이 (기본값: 1000)")

    class Config:
        json_schema_extra = {
            "example": {
                "urls": [
                    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "https://velog.io/@username/post-title",
                    "https://blog.naver.com/username/post-id"
                ]
            }
        }
