# IOSYS ItemBank AI API

AI 기반 차세대 문항은행 검색 시스템 API 서버

## 주요 기능

- **자연어 문항 검색**: "삼각형의 넓이를 구하시오" 같은 자연어 쿼리로 유사 문항 검색
- **유사 문항 검색**: item_id 기반 유사 문항 추천
- **RAG 기반 응답**: LLM을 활용한 문항 관련 질의응답
- **멀티모달 지원**: 텍스트 + 이미지 통합 검색 (예정)

## 기술 스택

| 구성요소 | 기술 |
|----------|------|
| Framework | FastAPI 0.128.0 |
| Embedding Model | Qwen3-VL-Embedding-2B |
| Vector Search | In-memory cosine similarity |
| Database | PostgreSQL + pgvector |
| LLM | OpenAI GPT (via LangChain) |
| Runtime | Python 3.12, CUDA 12.1 |

## 빠른 시작

### 1. 환경 설정

```bash
cd /mnt/sda/worker/dev_ldm/iosys-generative/itembank-api

# 가상환경 활성화
source .venv/bin/activate

# 환경 변수 설정 (.env 파일)
cp .env.example .env
# .env 파일 편집하여 필요한 값 설정
```

### 2. 서버 시작

```bash
# 개발 모드
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 프로덕션 모드
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### 3. API 테스트

```bash
# 헬스체크
curl http://localhost:8000/health

# 자연어 검색
curl -X POST http://localhost:8000/search/text \
  -H "Content-Type: application/json" \
  -d '{"query_text": "삼각형의 넓이를 구하시오", "top_k": 5}'
```

## 프로젝트 구조

```
itembank-api/
├── api/
│   ├── core/
│   │   ├── config.py      # 환경 설정 (Pydantic Settings)
│   │   └── deps.py        # 의존성 (DB Pool)
│   ├── models/
│   │   └── schemas.py     # Pydantic 스키마
│   ├── routers/
│   │   ├── health.py      # /health, /ready
│   │   ├── search.py      # /search/*
│   │   └── rag.py         # /rag/*
│   ├── services/
│   │   ├── qwen3vl.py     # Qwen3-VL 임베딩 서비스
│   │   ├── embedding.py   # 임베딩 검색 서비스
│   │   ├── database.py    # DB 서비스
│   │   └── llm.py         # LLM 서비스 (LangChain)
│   └── main.py            # FastAPI 앱 진입점
├── config/                # 설정 파일
├── scripts/               # 유틸리티 스크립트
├── requirements.txt       # Python 의존성
├── docker-compose.yml     # Docker 구성
├── API.md                 # API 문서
├── HANDOVER.md           # 작업 인수인계 문서
└── README.md             # 이 파일
```

## 환경 변수

`.env` 파일에 설정:

```bash
# Database
DB_HOST=localhost
DB_PORT=5433
DB_NAME=poc_itembank
DB_USER=poc_user
DB_PASSWORD=poc_password

# Embeddings
EMBEDDINGS_PATH=/path/to/embeddings.npz

# Qwen3-VL Model
QWEN3VL_MODEL_PATH=/path/to/qwen3-vl-embedding-2b
QWEN3VL_LAZY_LOAD=true

# OpenAI (RAG 기능 사용 시)
OPENAI_API_KEY=sk-...
```

## API 엔드포인트

### 검색 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/search/text` | 자연어 검색 (Qwen3VL 모델 사용) |
| POST | `/search/similar` | 유사 문항 검색 (item_id 또는 자연어) |
| POST | `/search/batch` | 배치 검색 |
| GET | `/search/items/{id}` | 문항 상세 조회 |

### RAG API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/rag/query` | RAG 질의응답 |
| POST | `/rag/generate` | 유사 문항 생성 |
| GET | `/rag/status` | RAG 서비스 상태 |

### 헬스체크

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 서버 상태 |
| GET | `/ready` | 서비스 준비 상태 |

상세 API 문서는 [API.md](./API.md) 참조

## 자연어 검색 사용 예시

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/search/text",
    json={
        "query_text": "삼각형의 넓이를 구하시오",
        "top_k": 5,
        "threshold": 0.3
    }
)

results = response.json()
for item in results["results"]:
    print(f"[{item['score']:.3f}] {item['metadata']['question_text']}")
```

### JavaScript

```javascript
const response = await fetch("http://localhost:8000/search/text", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    query_text: "삼각형의 넓이를 구하시오",
    top_k: 5,
    threshold: 0.3
  })
});

const data = await response.json();
console.log(data.results);
```

## 성능

| 항목 | 값 |
|------|-----|
| 첫 쿼리 (모델 로딩) | ~25-30초 |
| 이후 쿼리 | **0.8-1.0초** |
| 임베딩 수 | 176,443개 |
| 임베딩 차원 | 2,048 |
| GPU 메모리 | ~4.3GB |

## Docker 실행

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f api

# 종료
docker-compose down
```

## 개발

### 의존성 설치

```bash
# 가상환경 생성 (Python 3.12)
python3.12 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install transformers qwen-vl-utils accelerate
```

### 테스트

```bash
# 서버 시작
uvicorn api.main:app --reload

# API 테스트
curl http://localhost:8000/health
curl http://localhost:8000/docs  # Swagger UI
```

## 관련 문서

- [API 문서](./API.md) - 상세 API 명세
- [작업 인수인계](./HANDOVER.md) - 작업 이력 및 다음 작업자 가이드
- [프로젝트 마스터 플랜](../01%20IOSYS-ITEMBANK-AI-001.md)

## 라이선스

Internal Use Only - IOSYS
