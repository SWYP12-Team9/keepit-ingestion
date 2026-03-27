# Keepit Ingestion

> Keepit 링크 메타데이터 수집 API 서버

FastAPI 기반의 링크 메타데이터 수집 서비스입니다.
URL 유형을 판별해 플랫폼별 서비스로 위임하고, 일반 웹페이지는 정적 추출과 동적 렌더링을 조합해 처리합니다.

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| 언어 | Python 3.11+ |
| 프레임워크 | FastAPI, Uvicorn, Gunicorn |
| 정적 추출 | httpx, BeautifulSoup, Trafilatura |
| 동적 추출 | Playwright (Chromium) |
| 외부 fallback | Apify |
| YouTube | google-api-python-client, pytubefix, youtube-transcript-api |
| 테스트 | pytest |
| CI/CD | GitHub Actions, GCP Cloud Run |

## 🚀 주요 기능

### 1. 플랫폼별 처리

| 플랫폼 | 처리 방식 | 비고 |
|---|---|---|
| YouTube | YouTube Data API v3 -> `pytubefix` -> 기본 메타데이터 | 자막은 `youtube-transcript-api` 사용 |
| Instagram | Apify 기반 메타데이터 추출 | |
| 쿠팡 | 기본 메타데이터 생성 | |
| 네이버, 다음, 구글 검색 | URL 파라미터 파싱 ||
| 일반 웹사이트 | 정적 추출 -> 동적 렌더링 fallback | |

### 2. 일반 웹페이지 추출 흐름

```text
1. 정적 HTML 요청
2. DOM 본문 추출 시도
3. 본문이 부족하면 JSON-LD / hydration script 검사
4. JS 렌더링 필요 신호가 강하면 Playwright fallback
5. 그래도 실패하면 기본 메타데이터 반환
```

정적 본문 추출 시에는 `script`, `style`, `noscript`, `nav`, `footer`, `aside`, `form` 같은 명확한 보일러플레이트만 제거합니다.  
그 뒤 DOM 본문, JSON-LD, hydration payload를 순서대로 확인합니다.

### 3. 동적 렌더링 판단

다음과 같은 신호가 보이면 Playwright를 더 적극적으로 사용합니다.

- `#__next`, `#__nuxt`, `#root` 같은 SPA 루트
- loading/skeleton UI
- hydration script 존재
- 정적 DOM 본문이 너무 짧은 경우

### 4. 보안

- 사설 IP / 루프백 주소 차단
- 80, 443 이외 포트 차단
- `URL_BLOCKLIST` 지원
- `SSRF_ALLOWLIST` 지원

## 📦 프로젝트 구조

```text
keepit-ingestion/
├── app/
│   ├── main.py
│   └── scrapers/
│       ├── controller/
│       │   ├── scrape_api.py
│       │   └── scrape_controller.py
│       ├── dto/
│       │   └── scrape_response.py
│       ├── service/
│       │   ├── scrape_orchestrator.py
│       │   ├── platform/
│       │   │   ├── web_service.py
│       │   │   ├── youtube_service.py
│       │   │   ├── instagram_service.py
│       │   │   ├── google_service.py
│       │   │   ├── naver_service.py
│       │   │   ├── daum_service.py
│       │   │   └── coupang_service.py
│       │   ├── provider/
│       │   │   ├── playwright_provider.py
│       │   │   └── apify_provider.py
│       │   └── strategy/
│       │       ├── static_strategy.py
│       │       └── dynamic_strategy.py
│       └── utils/
│           ├── headers.py
│           └── scrape_utils.py
├── test/
│   ├── dto/
│   ├── platform/
│   ├── service/
│   ├── strategy/
│   └── utils/
├── .github/workflows/
│   ├── ci.yml
│   └── cd.yml
├── pytest.ini
└── requirements.txt
```

## 🏃 로컬 실행

### 사전 요구사항

- Python 3.11+
- Chromium 실행이 가능한 로컬 환경

### 설치

```bash
git clone https://github.com/SWYP12-Team9/keepit-ingestion.git
cd keepit-ingestion

python -m venv venv
source venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m playwright install chromium
```

### 개발 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 운영 형태 실행

```bash
gunicorn -w ${GUNICORN_WORKERS:-1} \
  -k uvicorn.workers.UvicornWorker \
  app.main:app \
  --bind 0.0.0.0:${PORT:-8000}
```

## ⚙️ 환경변수

`.env` 파일 예시:

```ini
LOG_LEVEL=INFO

SSRF_ALLOWLIST=
URL_BLOCKLIST=malicious.com,*.internal.net

APIFY_API_KEY=
YOUTUBE_API_KEY=

BROWSER_POOL_SIZE=4
```

## 🔗 API

문서:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

주요 엔드포인트:

- `POST /api/v1/scrape`
- `POST /api/v1/scrape/batch`

요청 예시:

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "max_length": 1000
}
```

응답 예시:

```json
{
  "success": true,
  "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
  "description": "The official video for...",
  "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
  "favicon_url": "https://www.youtube.com/favicon.ico",
  "site_name": "YouTube",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "content": "..."
}
```

참고:

- `content`는 실제 본문이나 자막이 확보된 경우에만 포함됩니다.
- 본문을 확실히 추출하지 못한 경우 `content`는 생략될 수 있습니다.

## 🧪 테스트

전체 테스트 실행:

```bash
python -m pytest test -q
```

특정 레이어만 실행:

```bash
python -m pytest test/utils -q
python -m pytest test/strategy -q
python -m pytest test/service -q
```

CI도 동일하게 `pytest` 기준으로 실행됩니다.

## ⚠️ 법적 고지

본 프로젝트는 개인 학습 및 팀 프로젝트 목적으로 개발되었습니다.

- 공개된 메타데이터와 접근 가능한 본문만 수집합니다.
- 로그인 우회나 비공개 콘텐츠 접근을 수행하지 않습니다.
- 수집된 본문은 요약/분석용 원본 데이터로만 사용합니다.
- 대상 사이트 정책이나 법적 요청에 따라 기능은 수정 또는 제거될 수 있습니다.
