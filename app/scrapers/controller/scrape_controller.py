import asyncio
from fastapi import APIRouter, HTTPException
from app.scrapers.service.scrape_orchestrator import scrape_url
from app.scrapers.controller.scrape_api import URLRequest, URLListRequest

router = APIRouter()

@router.post("/scrape")
async def scrape_url_post(request: URLRequest):
    """
    POST 메서드로 URL 메타데이터 추출
    """
    result = await scrape_url(request.url, max_length=request.max_length)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Failed to scrape URL")

    return result.to_dict()

@router.post("/scrape/batch")
async def scrape_urls_batch(request: URLListRequest):
    """
    여러 URL의 메타데이터를 한 번에 추출 (최대 10개)
    """
    results = await asyncio.gather(*[
        scrape_url(url, max_length=request.max_length) for url in request.urls
    ])

    success_count = sum(1 for r in results if r.success)
    failed_count = len(results) - success_count

    return {
        "total": len(request.urls),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": [result.to_dict() for result in results]
    }
