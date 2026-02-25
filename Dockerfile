FROM python:3.11-slim

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (lxml 등 파이썬 패키지 빌드 및 curl용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 종속성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright 및 Chromium 브라우저만 수동 설치 (용량 최적화)
# --with-deps를 사용하여 필요한 OS 라이브러리도 함께 설치
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*


# 애플리케이션 코드 및 환경 설정 파일 복사
COPY . .

# 포트 설정
EXPOSE 8000

# 애플리케이션 실행 (Cloud Run의 PORT 환경변수 대응)
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"
