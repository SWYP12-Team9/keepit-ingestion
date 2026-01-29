from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

from app.scrapers.controller.scrape_controller import router as scrape_router

# .env 파일 로드
load_dotenv()

app = FastAPI(
    title="URL Metadata Scraper API",
    description="다양한 웹사이트의 URL에서 title, description, content, 대표 이미지 등을 추출하는 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 스크래핑 API 라우터 포함
app.include_router(scrape_router, prefix="/api/v1", tags=["scrape"])
