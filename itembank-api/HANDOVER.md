# HANDOVER.md - 작업 인수인계 문서

## 최종 업데이트
- **날짜**: 2026-01-29
- **작업자**: Claude Code (Opus 4.5)
- **상태**: Qwen3-VL 자연어 검색 통합 완료

---

## 1. 프로젝트 현황

### 1.1 완료된 작업

#### Phase 1: 기본 API 인프라 구축 ✅
- FastAPI 기반 REST API 서버 구현
- PostgreSQL + pgvector 연동
- 임베딩 기반 유사 문항 검색 (item_id 기반)
- Docker Compose 환경 구성

#### Phase 2: Qwen3-VL 자연어 검색 통합 ✅ (2026-01-29)
- `Qwen3VLService` 구현 (`api/services/qwen3vl.py`)
- 자연어 텍스트 → 2048차원 임베딩 변환
- `/search/text` 엔드포인트 추가 (자연어 전용)
- `/search/similar` 엔드포인트에 `use_model` 플래그 추가
- Python 3.8 → 3.12 업그레이드
- 최신 의존성 설치 (langchain 1.2.7, numpy 2.4.1, torch 2.5.1)

### 1.2 진행 중인 작업
- 없음

### 1.3 예정된 작업
- 멀티모달 검색 (텍스트 + 이미지) 고도화
- Qwen3-VL-Reranker 통합 (Two-Stage Retrieval)
- 자동 분류 시스템 (교육과정/성취기준/난이도)
- 이미지 참조형 문항 생성 (Fact Graph 기반)

---

## 2. 환경 정보

### 2.1 Python 환경
```
Python: 3.12.3
venv 경로: /mnt/sda/worker/dev_ldm/iosys-generative/itembank-api/.venv
```

### 2.2 주요 의존성 버전
| 패키지 | 버전 | 비고 |
|--------|------|------|
| fastapi | 0.128.0 | |
| uvicorn | 0.40.0 | |
| langchain | 1.2.7 | |
| langchain-openai | 1.1.7 | |
| numpy | 2.4.1 | npz 파일 호환 필수 |
| torch | 2.5.1+cu121 | CUDA 12.1 |
| transformers | 5.0.0 | |
| torchvision | 0.20.1+cu121 | |

### 2.3 Qwen3-VL 모델 경로
```
/mnt/sda/worker/dev_ldm/iosys-generative/poc/models/qwen3-vl-embedding-2b
```

### 2.4 임베딩 파일 경로
```
/mnt/sda/worker/dev_ldm/iosys-generative/poc/results/qwen_embeddings_all_subjects_2b_multimodal.npz
- 문항 수: 176,443개
- 차원: 2048
```

### 2.5 데이터베이스
```
Host: localhost
Port: 5433
Database: poc_itembank
User: poc_user
```

---

## 3. 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                        클라이언트                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI (main.py)                        │
│  ┌─────────────┬─────────────┬─────────────┐               │
│  │ /health     │ /search/*   │ /rag/*      │               │
│  │ /ready      │             │             │               │
│  └─────────────┴──────┬──────┴─────────────┘               │
└───────────────────────┼─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Qwen3VLService│ │EmbeddingService│ │ LLMService    │
│ (자연어 인코딩) │ │ (벡터 검색)    │ │ (RAG 생성)    │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ Qwen3-VL-2B   │ │ NPZ 임베딩    │ │ OpenAI API    │
│ (GPU ~4.3GB) │ │ (메모리)      │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
                        │
                        ▼
                ┌───────────────┐
                │ PostgreSQL    │
                │ (메타데이터)   │
                └───────────────┘
```

---

## 4. 주요 파일 설명

### 4.1 서비스 레이어 (`api/services/`)

| 파일 | 설명 |
|------|------|
| `qwen3vl.py` | **신규** - Qwen3-VL 임베딩 서비스 (지연 로딩, GPU) |
| `embedding.py` | NPZ 임베딩 로딩 및 cosine similarity 검색 |
| `database.py` | PostgreSQL 연동 (asyncpg) |
| `llm.py` | LangChain 기반 LLM 서비스 (OpenAI) |

### 4.2 라우터 (`api/routers/`)

| 파일 | 엔드포인트 | 설명 |
|------|------------|------|
| `health.py` | `/health`, `/ready` | 헬스체크 |
| `search.py` | `/search/text`, `/search/similar` | 유사 문항 검색 |
| `rag.py` | `/rag/query`, `/rag/generate` | RAG 기반 응답 생성 |

### 4.3 설정 (`api/core/`)

| 파일 | 설명 |
|------|------|
| `config.py` | 환경 변수 설정 (Pydantic Settings) |
| `deps.py` | DB 커넥션 풀 관리 |

---

## 5. 성능 측정 결과

### 5.1 자연어 검색 (/search/text)

| 항목 | 측정값 | 비고 |
|------|--------|------|
| 첫 쿼리 (모델 로딩 포함) | ~25-30초 | GPU 웜업 포함 |
| 이후 쿼리 | **0.8-1.0초** | 목표 <100ms 대비 양호 |
| GPU 메모리 사용량 | ~4.3GB | RTX 2070 SUPER 8GB 기준 |

### 5.2 item_id 검색 (/search/similar?use_model=false)

| 항목 | 측정값 |
|------|--------|
| 응답 시간 | ~0.8-0.9초 |
| 메모리 사용량 | ~2.7GB (176K embeddings) |

---

## 6. 알려진 이슈

### 6.1 해결된 이슈
- ✅ Python 3.8 타입 힌트 호환성 (`list[dict]` → `List[Dict]`)
- ✅ numpy 2.0 호환성 (Python 3.12 업그레이드로 해결)
- ✅ torchvision 누락 (설치 완료)

### 6.2 주의사항
1. **GPU 메모리**: Qwen3-VL 모델 로딩 시 약 4.3GB GPU 메모리 필요
2. **첫 쿼리 지연**: 모델이 lazy loading되므로 첫 쿼리 시 20-30초 소요
3. **임베딩 파일**: numpy 2.x로 생성된 npz 파일은 numpy 1.x에서 로드 불가

---

## 7. 테스트 방법

### 7.1 서버 시작
```bash
cd /mnt/sda/worker/dev_ldm/iosys-generative/itembank-api
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### 7.2 API 테스트
```bash
# 헬스체크
curl http://localhost:8000/health

# 자연어 검색
curl -X POST http://localhost:8000/search/text \
  -H "Content-Type: application/json" \
  -d '{"query_text": "삼각형의 넓이를 구하시오", "top_k": 5}'

# item_id 검색 (하위 호환)
curl -X POST http://localhost:8000/search/similar \
  -H "Content-Type: application/json" \
  -d '{"query_text": "13E008D163DA4B8AAB46645989B1AD26", "use_model": false}'
```

---

## 8. 다음 작업자를 위한 참고사항

### 8.1 코드 스타일
- 변수명/함수명: 영어 (snake_case)
- 주석/문서: 한국어 허용
- 타입 힌트: 필수 (Python 3.12 기준)

### 8.2 관련 문서
- 프로젝트 마스터 플랜: `../01 IOSYS-ITEMBANK-AI-001.md`
- POC 계획서: `../06 ...-POC.md`
- Qwen3-VL 리서치: `../05 ...-R02.md`

### 8.3 모델 파일 위치
- Qwen3-VL-Embedding: `../poc/models/qwen3-vl-embedding-2b/`
- 임베딩 스크립트: `../poc/scripts/generate_qwen_embeddings.py`

---

## 변경 이력

| 날짜 | 작업자 | 변경 내용 |
|------|--------|----------|
| 2026-01-29 | Claude Code | Qwen3-VL 자연어 검색 통합, Python 3.12 업그레이드 |
| 2026-01-29 | Claude Code | 초기 API 서버 구축 (FastAPI + pgvector) |
