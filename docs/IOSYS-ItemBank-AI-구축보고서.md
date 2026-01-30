# IOSYS ItemBank AI 시스템 구축 보고서

---

## 표지

# IOSYS ItemBank AI
## AI 기반 차세대 문항은행 시스템 구축 보고서

**프로젝트명**: IOSYS ItemBank AI
**버전**: Phase 1 Complete
**작성일**: 2026년 1월

---

## 목차

1. **프로젝트 개요**
2. **시스템 아키텍처**
3. **데이터 전처리 (Preprocessing)**
4. **임베딩 모델 (POC)**
5. **백엔드 서비스 (itembank-api)**
6. **프론트엔드 (itembank-web)**
7. **성능 지표 및 결과**
8. **향후 계획**

---

## 1. 프로젝트 개요

### 1.1 프로젝트 목표

| 목표 | 설명 |
|------|------|
| 자연어 문항 검색 | Semantic Search 기반 의미적 유사도 검색 |
| 유사 문항 추천 | 벡터 임베딩 기반 유사 문항 자동 추천 |
| AI 문항 생성 | GPT-4o 기반 유사 문항 자동 생성 |
| 통합 검색 플랫폼 | 웹 기반 통합 검색 인터페이스 |

### 1.2 프로젝트 범위

```
Phase 1: 문항 벡터화 및 검색 인프라 ✅ 완료
Phase 2: 자동 분류 시스템 (계획)
Phase 3: 이미지 참조형 문항 생성 (계획)
Phase 4: 통합 플랫폼 및 API (계획)
```

### 1.3 핵심 성과

| 항목 | 수치 |
|------|------|
| 총 문항 수 | **176,443개** |
| 임베딩 차원 | 2,048차원 |
| 검색 P95 지연시간 | **30.5ms** |
| GPU 메모리 사용량 | 4.3GB |
| MRR (검색 정확도) | **0.74** |

---

## 2. 시스템 아키텍처

### 2.1 전체 시스템 구성도

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (itembank-web)                   │
│              Next.js 15 / React 19 / TypeScript              │
│         TanStack Query / Zustand / Tailwind CSS              │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                   Backend (itembank-api)                     │
│                     FastAPI / Python 3.12                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Qwen3-VL    │  │  Reranker   │  │   LLM Service       │  │
│  │ Embedding   │  │  Service    │  │  (LangChain+GPT-4o) │  │
│  │ (4.3GB GPU) │  │  (Optional) │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              PostgreSQL 16 + pgvector Extension              │
│           HNSW Index / Cosine Similarity Search              │
│                    176,443 Embeddings                        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 데이터 처리 파이프라인

```
IML 원본 파일 (184,761개)
        ↓
   Preprocessing (전처리)
        ↓
   POC (임베딩 생성)
        ↓
   itembank-api (서비스)
        ↓
   itembank-web (프론트엔드)
```

---

## 3. 데이터 전처리 (Preprocessing)

### 3.1 데이터 기술통계 개요

| 항목 | 수치 | 비율 |
|------|------|------|
| 총 IML 파일 | 184,761개 | 100% |
| 파싱 성공 | 176,443개 | **95.5%** |
| 검증 통과 | 131,460개 | 74.5% |
| 출력 용량 | 262 MB | 18개 JSON 파일 |

### 3.2 문항 유형별 분포

| 문항 유형 | 수량 | 비율 |
|----------|------|------|
| 선택형 (Multiple Choice) | 113,034 | **64.0%** |
| 완결형 (Completion) | 30,746 | 17.4% |
| 단답형 (Short Answer) | 26,450 | 15.0% |
| 서술형 (Essay) | 5,224 | 3.0% |
| 기타 (배합형 등) | 989 | 0.6% |

### 3.3 난이도별 분포

| 난이도 | 수량 | 비율 | 시각화 |
|--------|------|------|--------|
| 중 | 103,744 | **58.8%** | ████████████ |
| 하 | 39,833 | 22.6% | █████ |
| 상 | 24,955 | 14.1% | ███ |
| 중하 | 4,478 | 2.5% | █ |
| 상중 | 3,433 | 1.9% | █ |

### 3.4 과목별 분포

| 과목 | 수량 | 비율 | 시각화 |
|------|------|------|--------|
| 수학 | 80,548 | **45.7%** | █████████████████████ |
| 과학 | 35,125 | 19.9% | █████████ |
| 영어 | 17,098 | 9.7% | █████ |
| 역사 | 14,680 | 8.3% | ████ |
| 사회 | 14,614 | 8.3% | ████ |
| 국어 | 11,625 | 6.6% | ███ |

### 3.5 학년별 분포

| 학년 | 수량 | 비율 |
|------|------|------|
| 1학년 | 47,486 | **26.9%** |
| 2학년 | 46,346 | 26.3% |
| 3학년 | 34,509 | 19.6% |
| 4학년 | 9,736 | 5.5% |
| 공통 | 5,843 | 3.3% |

### 3.6 미디어 유형 분포

| 유형 | 수량 | 비율 |
|------|------|------|
| 텍스트 전용 | 131,075 | **74.3%** |
| 이미지 포함 | 45,368 | 25.7% |
| 총 이미지 수 | 53,175 | - |

### 3.7 연도별 분포 (상위 5개년)

| 연도 | 파일 수 | 비율 |
|------|---------|------|
| 2016 | 29,572 | **16.0%** |
| 2025 | 28,496 | 15.4% |
| 2021 | 19,413 | 10.5% |
| 2020 | 16,249 | 8.8% |
| 2019 | 13,118 | 7.1% |

**데이터 범위**: 2005년 ~ 2026년 (20년 이상)

### 3.8 전처리 파이프라인

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: 스키마 추출 (01_extract_schema.py)                  │
│ - 34개 고유 XML 태그 추출                                    │
│ - 태그 계층 구조 및 속성 매핑                                │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌────────────────────────┴────────────────────────────────────┐
│ Phase 2: IML 파싱 (02_parse_iml.py)                          │
│ - EUC-KR/CP949/UTF-8 인코딩 자동 감지                        │
│ - XML 파싱 및 메타데이터 추출                                │
│ - 출력: 176,443개 아이템                                     │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌────────────────────────┴────────────────────────────────────┐
│ Phase 3: 정규화 (03_preprocess.py)                           │
│ - LaTeX 수식 정규화                                          │
│ - 이미지 경로 검증                                           │
│ - 텍스트 클리닝                                              │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌────────────────────────┴────────────────────────────────────┐
│ Phase 4: 검증 (04_validate.py)                               │
│ - 필수 필드 검증                                             │
│ - 값 범위 검증                                               │
│ - 출력: 18개 JSON 파티션 파일                                │
└─────────────────────────────────────────────────────────────┘
```

### 3.9 IML 파일 구조

```xml
문항종류 (ROOT)
└── 단위문항
    └── 문항 [id, df, qt, cls1-9, kw, dyear, qs, qns]
        ├── 문제
        │   ├── 물음 → [문자열, 수식, 그림]
        │   └── 답항 (1-5)
        ├── 정답
        ├── 해석
        └── 해설
```

### 3.10 메타데이터 필드 (23개)

| 분류 | 필드명 | 설명 |
|------|--------|------|
| 식별자 | id | 32자리 UUID |
| 난이도 | df | 01-05 (상/상중/중/중하/하) |
| 유형 | qt | 11/31/34/41 |
| 분류체계 | cls1-cls9 | 교육과정~소단원 |
| 키워드 | kw | 공백/쉼표 구분 |
| 연도 | dyear | 생성 연도 |
| 출처 | qs, qns | 출처, 시험명 |

---

## 4. 임베딩 모델 (POC)

### 4.1 테스트 모델 비교

| 모델 | 차원 | GPU 메모리 | Top-5 Recall | 상태 |
|------|------|-----------|--------------|------|
| **Qwen3-VL-Embedding-2B** | 2,048 | 4.3GB | **85.2%** | ✅ 채택 |
| Qwen3-VL-Embedding-8B | 4,096 | 24GB | 70.5% | ❌ 비채택 |
| KURE-v1 (한국어) | 1,024 | 2.1GB | 33.4% | 대안 |
| SigLIP (이미지) | 768 | 1.5GB | 13.8% | 대안 |
| Combined (KURE+SigLIP) | 1,792 | 3.6GB | 33.0% | 대안 |

### 4.2 Qwen3-VL-Embedding-2B 선정 사유

| 평가 항목 | 목표 | 결과 | 판정 |
|-----------|------|------|------|
| P95 지연시간 | ≤200ms | **30.5ms** | ✅ PASS |
| GPU 메모리 | ≤8GB | **4.3GB** | ✅ PASS |
| Top-5 Recall | ≥80% | **85.2%** | ✅ PASS |
| MRR | ≥0.65 | **0.74** | ✅ PASS |

### 4.3 2B vs 8B 모델 비교

| 지표 | 2B 모델 | 8B 모델 | 차이 |
|------|---------|---------|------|
| Image GT Top-5 | **100.0%** | 92.6% | +7.4%p |
| Hybrid GT Top-5 | **85.2%** | 70.5% | +14.7%p |
| Image GT MRR | **90.6%** | 80.3% | +10.3%p |
| GPU 비용 | ~$0 | ~$4.5 | 절감 |

**결론**: 2B 모델이 8B보다 **더 우수한 성능** (모델 크기 ≠ 성능)

### 4.4 검색 전략 비교

| 전략 | Top-5 | Top-10 | MRR | MAP |
|------|-------|--------|-----|-----|
| **Dense Only (α=1.0)** | **83.7%** | **99.2%** | **49.8%** | **48.1%** |
| Dense 70% + BM25 30% | 71.2% | 91.8% | 43.6% | 43.3% |
| Hybrid 50/50 | 54.0% | 78.7% | 37.0% | 36.2% |
| BM25 Only | 44.7% | 52.0% | 29.9% | 25.8% |

**결론**: Dense-only 검색이 수학 문항에 가장 효과적

### 4.5 카테고리별 성능

| 카테고리 | Top-5 | Top-10 | MAP |
|----------|-------|--------|-----|
| 이미지 포함 | 80.6% | 100.0% | 41.1% |
| 텍스트 전용 | 84.2% | 97.4% | 46.8% |
| **LaTeX 수식** | **87.5%** | **100.0%** | **58.4%** |

### 4.6 Reranker 효과 분석

| 지표 | Baseline | +Reranker | 변화 |
|------|----------|-----------|------|
| Top-5 Recall | 40.4% | 38.8% | -1.6%p |
| **Top-10 Recall** | 51.4% | **55.4%** | **+4.0%p** ✅ |
| NDCG@10 | 52.5% | 53.5% | +1.0%p |

**권장**: 선택적 Reranking (Top-30→Top-10, 이미지 쿼리 제외)

### 4.7 임베딩 생성 결과

| 항목 | 수치 |
|------|------|
| 총 임베딩 수 | **176,443개** |
| 임베딩 차원 | 2,048 |
| 파일 크기 | 1.24 GB (.npz) |
| 생성 시간 | ~12.8시간 (RTX 2070 SUPER) |
| 이미지 포함 문항 | 41,322개 (23.4%) |

### 4.8 시스템 성능 벤치마크

| 지표 | 수치 |
|------|------|
| **P95 지연시간** | **30.5ms** |
| P99 지연시간 | 39.1ms |
| 평균 지연시간 | 23.2ms |
| 최소 지연시간 | 18.9ms |
| 최대 지연시간 | 75.2ms |
| 처리량 | 43.2 items/sec |
| 안정성 | 100% (1,000회 테스트) |

### 4.9 하드웨어 요구사항

| 컴포넌트 | 사양 |
|----------|------|
| GPU | NVIDIA RTX 2070 SUPER 8GB |
| CPU | Intel i7-11700KF (8-core) |
| RAM | 64GB DDR4 |
| Storage | 125GB+ |

---

## 5. 백엔드 서비스 (itembank-api)

### 5.1 기술 스택

| 컴포넌트 | 기술 | 버전 |
|----------|------|------|
| Framework | FastAPI | 0.128.0 |
| ASGI Server | Uvicorn | 0.40.0 |
| Database | PostgreSQL + pgvector | 16 + 0.7 |
| Async DB | asyncpg | 0.29.0 |
| LLM Framework | LangChain | 1.2.7 |
| LLM API | LangChain-OpenAI | 1.1.7 |
| ML Framework | PyTorch | 2.5.1+cu121 |
| Model Library | Transformers | 5.0.0 |

### 5.2 서비스 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Application                     │
│                         (main.py)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    ▼                      ▼                      ▼
┌─────────┐          ┌─────────┐           ┌─────────┐
│ Health  │          │ Search  │           │   RAG   │
│ Router  │          │ Router  │           │ Router  │
└─────────┘          └─────────┘           └─────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    ▼                      ▼                      ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Qwen3-VL     │  │   Database    │  │     LLM       │
│   Service     │  │   Service     │  │   Service     │
│  (4.3GB GPU)  │  │  (asyncpg)    │  │ (LangChain)   │
└───────────────┘  └───────────────┘  └───────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │  PostgreSQL   │
                   │   pgvector    │
                   └───────────────┘
```

### 5.3 API 엔드포인트

#### 검색 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/search/text` | 자연어 검색 (Qwen3-VL 인코딩) |
| POST | `/search/similar` | 유사 문항 검색 |
| POST | `/search/batch` | 배치 검색 |
| GET | `/search/items/{id}` | 문항 상세 조회 |
| GET | `/search/items/{id}/iml` | IML 원본 조회 |
| GET | `/search/images/{path}` | 이미지 서빙 |
| GET | `/search/ai-generated` | AI 생성 문항 목록 |

#### RAG API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/rag/query` | RAG 질의응답 |
| POST | `/rag/generate` | 문항 생성 |
| GET | `/rag/status` | RAG 서비스 상태 |
| POST | `/rag/clear-memory` | 대화 메모리 초기화 |

#### 생성 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/generate/item` | AI 문항 저장 |
| DELETE | `/generate/item/{id}` | AI 문항 삭제 |

#### 헬스체크

| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/health` | 기본 상태 확인 |
| GET | `/ready` | 서비스 준비 상태 |

### 5.4 핵심 서비스 컴포넌트

| 서비스 | 역할 | 특징 |
|--------|------|------|
| **Qwen3VLService** | 임베딩 생성 | Lazy Loading, 4.3GB GPU |
| **DatabaseService** | pgvector 검색 | Cosine Similarity, HNSW |
| **RerankerService** | 재순위화 | Cross-encoder |
| **LLMService** | RAG 생성 | GPT-4o, Chat Memory |
| **EmbeddingService** | NPZ 로딩 | In-memory Search |

### 5.5 데이터베이스 스키마

#### 임베딩 테이블

```sql
qwen_embeddings (PRIMARY)
├── id: VARCHAR(64) PK
├── embedding: vector(2048)  -- HNSW Index
└── created_at: TIMESTAMP
```

#### 문항 테이블

```sql
items
├── id: VARCHAR(64) PK
├── source_file: TEXT
├── question_type: VARCHAR(20)
├── difficulty: VARCHAR(10)
├── curriculum: VARCHAR(100)      -- cls1
├── school_level: VARCHAR(20)     -- cls2
├── grade: VARCHAR(20)            -- cls3
├── subject: VARCHAR(50)          -- cls4
├── subject_detail: VARCHAR(50)   -- cls5
├── semester: VARCHAR(20)         -- cls6
├── unit_large: VARCHAR(100)      -- cls7
├── unit_medium: VARCHAR(100)     -- cls8
├── unit_small: VARCHAR(100)      -- cls9
├── question_text: TEXT
├── choices: JSONB
├── answer_text: TEXT
├── explanation_text: TEXT
├── question_images: JSONB
├── has_image: BOOLEAN
├── keywords: TEXT
├── year: INTEGER
├── is_ai_generated: BOOLEAN
└── created_at, updated_at: TIMESTAMP
```

### 5.6 검색 파이프라인

```
사용자 쿼리
    ↓
Qwen3-VL 인코딩 (2048-dim 벡터)
    ↓
pgvector Cosine Search (HNSW)
    ↓
Top-100 후보 추출
    ↓
[선택] Reranker 재순위화
    ↓
Top-K 결과 반환 (메타데이터 포함)
```

### 5.7 서비스 성능

| 항목 | 수치 |
|------|------|
| 첫 쿼리 지연 | ~20-30초 (모델 로딩) |
| 후속 쿼리 지연 | ~800-1000ms |
| 벡터 검색 | ~100-200ms |
| RAG 생성 | ~1500-2000ms |
| Reranking | ~200-300ms |

### 5.8 메모리 사용량

| 컴포넌트 | 메모리 |
|----------|--------|
| Qwen3-VL (GPU) | 4.3GB |
| Embeddings (NPZ) | 2.7GB |
| DB Connection Pool | 100-200MB |
| Reranker (GPU) | 2.5GB |
| **총 GPU 메모리** | **~6.8GB** |

---

## 6. 프론트엔드 (itembank-web)

### 6.1 기술 스택

| 컴포넌트 | 기술 | 버전 |
|----------|------|------|
| Framework | Next.js | 15.1.9 |
| UI Library | React | 19.0.0 |
| Language | TypeScript | 5.7.0 |
| State (Server) | TanStack React Query | 5.60.0 |
| State (Client) | Zustand | 5.0.0 |
| Styling | Tailwind CSS | 3.4.0 |
| Animation | Framer Motion | 12.29.2 |
| Math Rendering | KaTeX | 0.16.0 |

### 6.2 워크스페이스 패키지

| 패키지 | 역할 |
|--------|------|
| @iosys/qti-core | QTI 파싱 및 타입 정의 |
| @iosys/qti-ui | QTI 스타일 컴포넌트 |
| @iosys/qti-viewer | QTI 문항 뷰어 |

### 6.3 컴포넌트 구조

```
src/
├── app/
│   ├── page.tsx          # 메인 검색 페이지
│   ├── layout.tsx        # 루트 레이아웃
│   ├── providers.tsx     # React Query Provider
│   └── globals.css
├── components/
│   ├── QtiItemViewer.tsx       # 문항 렌더러
│   ├── LazyQtiItemViewer.tsx   # Lazy Loading
│   ├── StateViews.tsx          # 상태 뷰
│   ├── MathText.tsx            # 수식 렌더링
│   ├── cards/
│   │   └── index.tsx           # 카드 컴포넌트
│   ├── badges/
│   │   └── index.tsx           # 배지 컴포넌트
│   ├── icons/
│   │   └── index.tsx           # 아이콘
│   └── modals/
│       └── GenerationModal.tsx # AI 생성 모달
├── lib/
│   ├── api.ts            # API 클라이언트
│   └── store.ts          # Zustand 스토어
└── types/
    └── api.ts            # TypeScript 타입
```

### 6.4 주요 기능

| 기능 | 설명 |
|------|------|
| **자연어 검색** | Qwen3-VL 기반 시맨틱 검색 |
| **유사 문항 검색** | 선택 문항 기반 유사도 검색 |
| **문항 렌더링** | IML/QTI + LaTeX + 이미지 |
| **AI 문항 생성** | GPT-4o 기반 유사 문항 생성 |
| **정답/해설 토글** | 접기/펼치기 UI |

### 6.5 UI 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ Header: 로고 / 검색바 / 통계                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [검색 모드]                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  검색 결과 그리드 (1-3열 반응형)                      │   │
│  │  ┌─────┐ ┌─────┐ ┌─────┐                            │   │
│  │  │Card │ │Card │ │Card │ ...                        │   │
│  │  └─────┘ └─────┘ └─────┘                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [선택 모드]                                                 │
│  ┌──────────┬──────────────────────────────────────────┐   │
│  │ 1/4      │ 3/4                                      │   │
│  │ Selected │ Similar Items Grid                       │   │
│  │ Item     │ ┌─────┐ ┌─────┐ ┌─────┐                 │   │
│  │ Detail   │ │Card │ │Card │ │Card │ ...             │   │
│  │          │ └─────┘ └─────┘ └─────┘                 │   │
│  └──────────┴──────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 6.6 상태 관리

#### TanStack React Query (서버 상태)

```typescript
// 검색 결과
useQuery(['search', query], () => api.searchText(query))

// 유사 문항
useQuery(['similar', itemId], () => api.searchSimilar(itemId))

// AI 생성 문항
useQuery(['ai-generated', itemId], () => api.getAiGeneratedItems(itemId))

// IML 콘텐츠
useQuery(['iml', itemId], () => api.getItemIml(itemId))
```

#### Zustand (클라이언트 상태)

```typescript
interface AppState {
  selectedItem: SearchResultItem | null
  searchQuery: string
  searchHistory: string[]  // 최근 10개
}
```

### 6.7 API 통합

| 엔드포인트 | 용도 |
|------------|------|
| POST `/api/search/text` | 자연어 검색 |
| POST `/api/search/similar` | 유사 문항 검색 |
| GET `/api/search/items/{id}` | 문항 상세 |
| GET `/api/search/items/{id}/iml` | IML 콘텐츠 |
| POST `/api/generate/similar` | AI 문항 생성 |
| POST `/api/generate/save` | AI 문항 저장 |

### 6.8 디자인 시스템

| 요소 | 값 |
|------|-----|
| Primary Color | Indigo (#4F46E5) |
| Accent Color | Emerald (#10B981) |
| Font | Pretendard Variable |
| Border Radius | 0 (Flat Design) |
| Shadow | None |

### 6.9 배지 컴포넌트

| 배지 | 용도 | 색상 |
|------|------|------|
| SimilarityBadge | 유사도 % | Green ≥80%, Amber ≥60%, Gray <60% |
| DifficultyBadge | 난이도 | Red (상), Amber (중), Green (하) |
| AIBadge | AI 생성 표시 | Gradient (Purple-Pink) |

---

## 7. 성능 지표 및 결과

### 7.1 검색 품질 지표

| 지표 | Image GT | Hybrid GT | 목표 |
|------|----------|-----------|------|
| **Top-1 Recall** | 85.2% | 29.5% | - |
| **Top-3 Recall** | 92.6% | 77.0% | - |
| **Top-5 Recall** | **100.0%** | **85.2%** | ≥80% ✅ |
| **Top-10 Recall** | 100.0% | 88.5% | - |
| **MRR** | 90.6% | 54.4% | ≥0.65 ✅ |

### 7.2 시스템 성능 지표

| 지표 | 목표 | 결과 | 판정 |
|------|------|------|------|
| P95 지연시간 | ≤200ms | **30.5ms** | ✅ PASS |
| GPU 메모리 | ≤8GB | **4.3GB** | ✅ PASS |
| 처리량 | - | 43.2 items/sec | - |
| 안정성 | 100% | **100%** | ✅ PASS |

### 7.3 데이터 품질 지표

| 지표 | 수치 |
|------|------|
| IML 파싱 성공률 | **95.5%** |
| 데이터 검증률 | 74.5% |
| 이미지 검증률 | 99.998% (53,174/53,175) |

### 7.4 LLM 정렬 검증

| 지표 | 수치 |
|------|------|
| LLM Top-10 Recall | **99.3%** |
| 해석 | GPT-4o가 선택한 99.3%가 임베딩 Top-10에 존재 |

---

## 8. 향후 계획

### 8.1 Phase 2: 자동 분류 시스템

- 교육과정 자동 분류
- 성취기준 매핑
- 난이도 예측 모델

### 8.2 Phase 3: 이미지 참조형 문항 생성

- Fact Graph 추출 파이프라인
- Integrity Gate 검증
- Hallucination 방지 시스템

### 8.3 Phase 4: 통합 플랫폼

- 관리자 UI 대시보드
- 모니터링 시스템
- Qwen3-VL-Reranker 통합

### 8.4 개선 과제

| 영역 | 과제 |
|------|------|
| 데이터 | Ground Truth 수동 레이블링 |
| 모델 | 다른 과목 검증 확대 |
| 서비스 | 멀티모달 Reranker 적용 |
| 인프라 | 대규모 스케일링 테스트 |

---

## 부록

### A. 환경 변수 설정

```bash
# Database
DB_HOST=localhost
DB_PORT=5433
DB_NAME=poc_itembank
DB_USER=poc_user
DB_PASSWORD=poc_password

# Embeddings
EMBEDDINGS_PATH=/path/to/embeddings.npz
QWEN3VL_MODEL_PATH=/path/to/qwen3-vl-embedding-2b

# LLM
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Reranker
USE_RERANKER=true
RERANKER_MODEL_PATH=/path/to/qwen3-vl-reranker-2b
```

### B. Docker Compose 구성

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    ports: ["5433:5432"]

  api:
    build: ./itembank-api
    ports: ["8000:8000"]
    depends_on: [db]

  web:
    build: ./itembank-web
    ports: ["3000:3000"]
    depends_on: [api]
```

### C. 주요 디렉토리 구조

```
iosys-generative/
├── preprocessing/          # 데이터 전처리
├── poc/                    # 임베딩 POC
├── itembank-api/           # 백엔드 서비스
├── itembank-web/           # 프론트엔드
├── qti-components/         # QTI 컴포넌트 라이브러리
├── data/
│   ├── raw/               # IML 원본 (184,761개)
│   └── processed/         # 처리된 JSON (18개)
└── docs/                   # 문서
```

---

**문서 끝**

*본 보고서는 IOSYS ItemBank AI Phase 1 구축 완료 시점을 기준으로 작성되었습니다.*
