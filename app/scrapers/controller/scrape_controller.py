from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.scrapers.service.scrape import scrape_url
from app.scrapers.controller.scrape_api import URLRequest, URLListRequest

router = APIRouter()

@router.get("/scrape")
def scrape_url_get(
    url: str = Query(..., description="스크래핑할 URL을 입력하세요"),
    max_length: Optional[int] = Query(1000, description="본문 미리보기 최대 길이 (기본값: 1000)")
):
    """
    GET 메서드로 URL 메타데이터 추출
    """
    result = scrape_url(url, max_length=max_length)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to scrape URL"))

    return result

@router.post("/scrape")
def scrape_url_post(request: URLRequest):
    """
    POST 메서드로 URL 메타데이터 추출
    """
    result = scrape_url(request.url, max_length=request.max_length)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to scrape URL"))

    return result

@router.post("/scrape/batch")
def scrape_urls_batch(request: URLListRequest):
    """
    여러 URL의 메타데이터를 한 번에 추출 (최대 10개)
    """
    results = []
    success_count = 0
    failed_count = 0

    for url in request.urls:
        result = scrape_url(url, max_length=request.max_length)
        results.append(result)

        if result.get("success"):
            success_count += 1
        else:
            failed_count += 1

    return {
        "total": len(request.urls),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results
    }
