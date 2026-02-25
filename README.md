# Keepit Ingestion

> Keepit 링크 메타데이터 수집 API 서버

FastAPI 기반의 웹 메타데이터 수집 서비스입니다. 메타데이터 추출 파이프라인을 제공합니다.

---

## 🛠️ 기술 스택

| 분류 | 기술 |
|---|---|
| 언어 | Python 3.11 |
| 프레임워크 | FastAPI, Uvicorn |
| 스크래퍼 | BeautifulSoup, Trafilatura, Playwright (Chromium), Apify |
| 미디어 | yt-dlp, youtube-transcript-api |
| 컨테이너 | Docker, Docker Compose |
| 배포 | GCP Cloud Run, Artifact Registry |
| CI/CD | GitHub Actions |

---

## 🚀 주요 기능

### 1. 플랫폼별 스크래퍼

| 플랫폼 | 추출 정보 | 특이사항 |
|---|---|---|
| **YouTube** | 제목, 설명, 썸네일, 채널 아이콘, 자막 | 쿠키 인증 기반 안정적 요청 처리 |
| **Instagram** | 게시물 메타데이터 | Apify API 기반 |
| **쿠팡** | 상품명, 설명, 이미지 | Apify API 기반 메타데이터 수집 |
| **네이버 블로그** | 제목, 본문, 썸네일 | PostView URL 변환으로 본문 접근 |
| **네이버 지도/검색** | 검색어, 메타데이터 | URL 파라미터 파싱 |
| **다음 검색** | 검색어, 메타데이터 | URL 디코딩 |
| **일반 웹사이트** | OG 태그, HTML 메타데이터 | 범용 파서 |

### 2. 3단계 폴백 전략

```
1차: 정적 메타데이터 파싱 (BeautifulSoup + Trafilatura)
 ↓ 실패 시
2차: 동적 렌더링 수집 (Playwright + Chromium)
 ↓ 실패 시  
3차: 외부 API 수집 (Apify)
 ↓ 실패 시
기본 메타데이터 반환 (도메인명 기반)
```

### 3. 보안 (SSRF 방지)

- **사설 IP 차단**: `127.0.0.1`, `192.168.x.x`, `10.x.x.x` 등 내부 네트워크 요청 차단
- **포트 제한**: 80(HTTP), 443(HTTPS) 포트만 허용
- **도메인 차단 목록**: 환경변수 `URL_BLOCKLIST`로 특정 도메인 차단 (와일드카드 지원)
- **허용 목록**: `SSRF_ALLOWLIST`로 내부 호스트 예외 처리

---

## 📦 프로젝트 구조

```
keepit-ingestion/
├── app/
│   ├── main.py                          # FastAPI 앱 진입점
│   └── scrapers/
│       ├── service/
│       │   ├── scrape.py                # 메타데이터 수집 파이프라인 (메인 로직)
│       │   ├── web.py                   # 범용 웹 스크래퍼
│       │   ├── youtube.py               # YouTube 스크래퍼
│       │   ├── coupang.py               # 쿠팡 스크래퍼
│       │   ├── naver.py                 # 네이버 스크래퍼
│       │   ├── daum.py                  # 다음 스크래퍼
│       │   ├── playwright_scraper.py    # Playwright 동적 스크래퍼
│       │   └── apify_scraper.py         # Apify 폴백 스크래퍼
│       └── utils/
│           └── scrape_utils.py          # 유틸리티 함수
├── test/                                # 테스트
├── .github/workflows/
│   ├── ci.yml                           # PR 시 테스트 자동 실행
│   └── cd.yml                           # main 머지 시 Cloud Run 배포
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🏃 실행 방법

### 사전 요구사항
- Python 3.11+
- Docker & Docker Compose (선택)

### 로컬 개발

```bash
# 저장소 클론
git clone https://github.com/SWYP12-Team9/keepit-ingestion.git
cd keepit-ingestion

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install --with-deps chromium

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Docker Compose로 실행
docker compose up -d --build
```

---

## ⚙️ 환경변수 설정 (.env)

프로젝트 루트에 `.env` 파일을 생성합니다:

```ini
# 로깅
LOG_LEVEL=INFO

# 보안 (선택)
SSRF_ALLOWLIST=                              # 허용할 내부 호스트 (쉼표 구분)
URL_BLOCKLIST=malicious.com,*.internal.net   # 차단할 도메인

# 외부 API (선택)
APIFY_API_KEY=your_apify_key                 # Apify 스크래핑용
```

---

## 🔗 API 문서

서버 실행 후 아래 주소에서 API 문서를 확인할 수 있습니다:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 메인 엔드포인트

**POST** `/api/v1/scrape`

**요청:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**응답:**
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

---

## 🧪 테스트

```bash
# 전체 테스트 실행
python -m unittest discover test

# 특정 테스트 실행
python -m unittest test/test_api.py
```

---

## ⚠️ 법적 고지 (Disclaimer)

본 프로젝트는 **개인 학습 및 팀 프로젝트 목적**으로 개발되었습니다.

- 본 서비스는 사용자가 입력한 URL의 **공개된 메타데이터**(Open Graph 태그, HTML meta 태그 등)를 수집합니다. 이는 카카오톡, 슬랙 등의 서비스가 **링크 미리보기를 생성하는 것과 동일한 방식**입니다.
- 수집된 본문은 **AI 요약을 위한 원본 데이터**로만 활용되며, 원문 자체가 외부에 공개되지 않습니다. 요약문은 원본 콘텐츠를 대체하지 않으며, 사용자가 **원본 링크에 접근하도록 유도하는 참고 정보**로 제공됩니다.
- 로그인이 필요한 비공개 콘텐츠에 대한 접근이나 인증 우회를 수행하지 않으며, 사용자 요청 1건당 1회의 메타데이터 수집만 이루어집니다.
- 본 프로젝트는 대상 사이트에 과도한 트래픽을 발생시키지 않도록 설계되었으며, **상업적 목적의 대량 데이터 수집이나 저작권 침해를 의도하지 않습니다.**
- 각 플랫폼의 정책 변경 또는 법적 요청이 있을 경우, 해당 기능은 즉시 수정 또는 제거됩니다.