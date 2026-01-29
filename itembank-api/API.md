# API Documentation

IOSYS ItemBank AI - 문항 검색 API 문서

**Base URL**: `http://localhost:8000`
**API Version**: 1.0.0

---

## 목차

1. [헬스체크](#1-헬스체크)
2. [검색 API](#2-검색-api)
3. [RAG API](#3-rag-api)
4. [에러 응답](#4-에러-응답)

---

## 1. 헬스체크

### GET /health

서버 상태 확인

**Response**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

### GET /ready

서비스 준비 상태 확인 (DB, 임베딩 로딩 상태)

**Response**
```json
{
  "status": "ready",
  "database": "connected",
  "embeddings": "loaded"
}
```

---

## 2. 검색 API

### POST /search/text

**자연어 텍스트로 유사 문항 검색** (Qwen3-VL 모델 사용)

자연어 쿼리를 Qwen3-VL-Embedding 모델로 임베딩 변환 후 유사 문항 검색

**Request Body**
```json
{
  "query_text": "삼각형의 넓이를 구하시오",
  "query_image": null,
  "top_k": 10,
  "threshold": 0.5
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `query_text` | string | Yes | 검색할 자연어 텍스트 |
| `query_image` | string | No | 이미지 파일 경로 (멀티모달 검색 시) |
| `top_k` | integer | No | 반환할 결과 수 (기본: 10, 최대: 100) |
| `threshold` | float | No | 최소 유사도 임계값 (기본: 0.5, 범위: 0.0-1.0) |

**Response**
```json
{
  "results": [
    {
      "item_id": "13E008D163DA4B8AAB46645989B1AD26",
      "score": 0.4025,
      "metadata": {
        "id": "13E008D163DA4B8AAB46645989B1AD26",
        "question_text": "삼각형의 넓이를 구하시오.",
        "question_type": "완결형",
        "difficulty": "하",
        "school_level": "중학교",
        "grade": "2학년",
        "subject": "수학",
        "unit_large": "수와 식",
        "unit_medium": "식의 계산",
        "has_image": false
      }
    }
  ],
  "query_time_ms": 894.63,
  "total_count": 5
}
```

**Example**
```bash
curl -X POST http://localhost:8000/search/text \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "삼각형의 넓이를 구하시오",
    "top_k": 5,
    "threshold": 0.3
  }'
```

**Notes**
- 첫 번째 요청 시 모델 로딩으로 20-30초 소요
- 이후 요청은 약 1초 내외

---

### POST /search/similar

**유사 문항 검색** (item_id 또는 자연어)

`use_model` 플래그에 따라 검색 방식 선택

**Request Body**
```json
{
  "query_text": "13E008D163DA4B8AAB46645989B1AD26",
  "query_image": null,
  "top_k": 10,
  "threshold": 0.5,
  "use_model": false
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `query_text` | string | Yes | 검색 쿼리 (item_id 또는 자연어) |
| `query_image` | string | No | 이미지 파일 경로 (use_model=true 시) |
| `top_k` | integer | No | 반환할 결과 수 (기본: 10) |
| `threshold` | float | No | 최소 유사도 임계값 (기본: 0.5) |
| `use_model` | boolean | No | **false**: item_id로 임베딩 조회, **true**: Qwen3VL로 임베딩 생성 |

**use_model=false (기본값)**
- `query_text`를 item_id로 해석
- 해당 문항의 기존 임베딩을 사용하여 유사 문항 검색
- item_id가 존재하지 않으면 빈 결과 반환

**use_model=true**
- `query_text`를 자연어로 해석
- Qwen3-VL 모델로 실시간 임베딩 생성
- `/search/text`와 동일한 동작

**Response**
```json
{
  "results": [
    {
      "item_id": "13E008D163DA4B8AAB46645989B1AD26",
      "score": 1.0,
      "metadata": { ... }
    },
    {
      "item_id": "ED41D904640F4C198E2ACAB21C1AEE89",
      "score": 0.9706,
      "metadata": { ... }
    }
  ],
  "query_time_ms": 877.64,
  "total_count": 3
}
```

**Example - item_id 검색**
```bash
curl -X POST http://localhost:8000/search/similar \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "13E008D163DA4B8AAB46645989B1AD26",
    "use_model": false,
    "top_k": 3
  }'
```

**Example - 자연어 검색**
```bash
curl -X POST http://localhost:8000/search/similar \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "피타고라스 정리 문제",
    "use_model": true,
    "top_k": 5,
    "threshold": 0.2
  }'
```

---

### POST /search/batch

**배치 검색** (여러 쿼리 동시 처리)

**Request Body**
```json
{
  "queries": [
    {"query_text": "삼각형 넓이", "top_k": 3, "use_model": true},
    {"query_text": "원의 둘레", "top_k": 3, "use_model": true}
  ]
}
```

**Response**
```json
{
  "results": [
    {
      "results": [...],
      "query_time_ms": 890.5,
      "total_count": 3
    },
    {
      "results": [...],
      "query_time_ms": 850.2,
      "total_count": 3
    }
  ],
  "total_time_ms": 1742.3
}
```

---

### GET /search/items/{item_id}

**문항 상세 조회**

**Parameters**
| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `item_id` | string | 문항 ID (UUID 형식) |

**Response**
```json
{
  "item_id": "13E008D163DA4B8AAB46645989B1AD26",
  "category": "text_only",
  "difficulty": "하",
  "question_type": "완결형",
  "question_text": "삼각형의 넓이를 구하시오.",
  "has_image": false,
  "metadata": {
    "school_level": "중학교",
    "grade": "2학년",
    "subject": "수학",
    "unit_large": "수와 식"
  }
}
```

**Example**
```bash
curl http://localhost:8000/search/items/13E008D163DA4B8AAB46645989B1AD26
```

---

## 3. RAG API

### POST /rag/query

**RAG 기반 질의응답**

검색 결과를 컨텍스트로 활용하여 LLM이 답변 생성

**Request Body**
```json
{
  "query": "삼각형 넓이 공식을 알려주세요",
  "item_id": null,
  "top_k": 5,
  "threshold": 0.3,
  "use_memory": false,
  "session_id": "default"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `query` | string | Yes | 사용자 질문 |
| `item_id` | string | No | 참조할 문항 ID |
| `top_k` | integer | No | 검색할 문항 수 (기본: 5) |
| `threshold` | float | No | 유사도 임계값 (기본: 0.3) |
| `use_memory` | boolean | No | 대화 기록 유지 여부 |
| `session_id` | string | No | 세션 ID (use_memory=true 시) |

**Response**
```json
{
  "answer": "삼각형의 넓이는 (밑변 × 높이) ÷ 2 로 계산합니다...",
  "sources": [
    {"item_id": "13E008D163DA4B8AAB46645989B1AD26", "score": 0.85}
  ],
  "query_time_ms": 2500.5,
  "retrieval_time_ms": 900.2,
  "generation_time_ms": 1600.3
}
```

**Notes**
- `OPENAI_API_KEY` 환경 변수 설정 필요
- 설정되지 않으면 503 에러 반환

---

### POST /rag/generate

**유사 문항 생성**

참조 문항을 기반으로 새로운 문항 생성

**Request Body**
```json
{
  "reference_item_ids": ["13E008D163DA4B8AAB46645989B1AD26"],
  "instructions": "난이도를 높여서 생성해주세요"
}
```

**Response**
```json
{
  "generated_question": "직각삼각형에서 두 변의 길이가 3, 4일 때...",
  "reference_items": [
    {"item_id": "13E008D163DA4B8AAB46645989B1AD26"}
  ],
  "generation_time_ms": 1800.5
}
```

---

### GET /rag/status

**RAG 서비스 상태 확인**

**Response**
```json
{
  "llm_configured": true,
  "embeddings_loaded": true,
  "embedding_count": 176443,
  "framework": "langchain"
}
```

---

### POST /rag/clear-memory

**대화 메모리 초기화**

**Response**
```json
{
  "status": "memory cleared"
}
```

---

## 4. 에러 응답

### 에러 형식

```json
{
  "detail": "에러 메시지"
}
```

### HTTP 상태 코드

| 코드 | 설명 |
|------|------|
| 200 | 성공 |
| 400 | 잘못된 요청 (파라미터 오류) |
| 404 | 리소스를 찾을 수 없음 (item_id 없음) |
| 500 | 서버 내부 오류 (모델 인코딩 실패 등) |
| 503 | 서비스 불가 (임베딩 미로드, LLM 미설정) |

### 주요 에러 메시지

| 메시지 | 원인 | 해결 방법 |
|--------|------|----------|
| `Embedding service not ready` | 임베딩 파일 로딩 실패 | NPZ 파일 경로 확인 |
| `Qwen3VL service not initialized` | 모델 서비스 초기화 안됨 | 설정 확인 |
| `Failed to encode query with Qwen3VL model` | 모델 인코딩 실패 | GPU 메모리, 의존성 확인 |
| `LLM service not configured` | OpenAI API 키 없음 | OPENAI_API_KEY 설정 |
| `Item {item_id} not found` | 문항 ID 없음 | ID 확인 |

---

## 5. 메타데이터 필드 설명

검색 결과의 `metadata` 객체에 포함되는 필드:

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | string | 문항 고유 ID |
| `question_text` | string | 문제 텍스트 |
| `question_type` | string | 문항 유형 (완결형, 단답형, 서술형 등) |
| `difficulty` | string | 난이도 (상, 중, 하) |
| `curriculum` | string | 교육과정 |
| `school_level` | string | 학교급 (초등, 중학교, 고등학교) |
| `grade` | string | 학년 |
| `subject` | string | 과목 |
| `unit_large` | string | 대단원 |
| `unit_medium` | string | 중단원 |
| `unit_small` | string | 소단원 |
| `answer_text` | string | 정답 |
| `explanation_text` | string | 해설 |
| `has_image` | boolean | 이미지 포함 여부 |
| `category` | string | 분류 (text_only, with_image) |

---

## 6. OpenAPI 문서

Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`
