# Qwen3-VL-Embedding 종합 기술 리서치 보고서

**문서 ID**: IOSYS-ITEMBANK-AI-001-R02  
**버전**: v1.0.0  
**작성일**: 2026-01-27  
**상위 문서**: IOSYS-ITEMBANK-AI-001-T01 (Phase 1 태스크 목록)  
**작성자**: AI 기반 문항은행 시스템 구축 TF

---

## 목차

1. [모델 개요](#1-모델-개요)
2. [핵심 기능](#2-핵심-기능)
3. [아키텍처 상세](#3-아키텍처-상세)
4. [벤치마크 성능](#4-벤치마크-성능)
5. [고급 기능](#5-고급-기능)
6. [다국어 지원](#6-다국어-지원)
7. [사용 예시](#7-사용-예시)
8. [하드웨어 요구사항](#8-하드웨어-요구사항)
9. [프로젝트 적용 전략](#9-프로젝트-적용-전략)
10. [권장 의사결정 프로세스](#10-권장-의사결정-프로세스)
11. [리스크 및 완화 방안](#11-리스크-및-완화-방안)
12. [결론 및 권장사항](#12-결론-및-권장사항)
13. [참고 문헌](#13-참고-문헌)

---

## 1. 모델 개요

### 1.1 출시 정보

| 항목 | 내용 |
|------|------|
| **출시일** | 2026년 1월 8일 |
| **개발팀** | Alibaba Tongyi Lab (Qwen Team) |
| **논문** | arXiv:2601.04720 |
| **라이선스** | Apache 2.0 (오픈소스) |
| **저장소** | GitHub, Hugging Face, ModelScope |

### 1.2 모델 사양

| 모델 | 파라미터 | 임베딩 차원 | 최대 토큰 | MRL 지원 | 양자화 지원 |
|------|----------|------------|-----------|----------|-------------|
| **Qwen3-VL-Embedding-2B** | 2B | 유연 (MRL) | 32K | ✅ | ✅ |
| **Qwen3-VL-Embedding-8B** | 8B | 유연 (MRL) | 32K | ✅ | ✅ |
| **Qwen3-VL-Reranker-2B** | 2B | - | 32K | - | - |
| **Qwen3-VL-Reranker-8B** | 8B | - | 32K | - | - |

### 1.3 모델 다운로드 링크

- **Hugging Face**: https://huggingface.co/collections/Qwen/qwen3-vl-embedding
- **GitHub**: https://github.com/QwenLM/Qwen3-VL-Embedding
- **ModelScope**: https://modelscope.cn/models/qwen/Qwen3-VL-Embedding-2B

---

## 2. 핵심 기능

### 2.1 멀티모달 통합

Qwen3-VL-Embedding은 다양한 모달리티를 단일 임베딩 공간에 매핑합니다.

```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Representation Space              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  Text   │  │  Image  │  │ Screen- │  │  Video  │        │
│  │         │  │         │  │  shot   │  │         │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│       └────────────┴────────────┴────────────┘              │
│                         │                                    │
│                         ▼                                    │
│               Qwen3-VL-Embedding                             │
│                         │                                    │
│                         ▼                                    │
│              Dense Vector (Unified)                          │
└─────────────────────────────────────────────────────────────┘
```

**지원 입력 모달리티**:

| 모달리티 | 설명 | 예시 |
|----------|------|------|
| **텍스트** | 순수 텍스트, 쿼리, 문서 | 문항 텍스트, 검색 쿼리 |
| **이미지** | 사진, 그래프, 다이어그램, 도형 | 수학 그래프, 과학 실험 이미지 |
| **스크린샷** | 문서 이미지, UI 캡처 | PDF 페이지, 문서 스캔 |
| **비디오** | 동영상 프레임 | 실험 영상, 교육 콘텐츠 |
| **혼합** | 텍스트+이미지, 텍스트+비디오 | 문항(텍스트) + 그래프(이미지) |

### 2.2 Two-Stage 검색 파이프라인

```
Query ─────────────────────────────────────────────────────────►
         │                                                      
         ▼                                                      
┌─────────────────────┐                                        
│ Qwen3-VL-Embedding  │  Stage 1: Initial Recall              
│  (Bi-Encoder)       │  - Dense Vector 생성                   
│                     │  - Cosine Similarity 검색              
│                     │  - Top-K 후보 추출                     
└──────────┬──────────┘                                        
           │ Top-K Candidates                                   
           ▼                                                    
┌─────────────────────┐                                        
│ Qwen3-VL-Reranker   │  Stage 2: Re-ranking                  
│  (Cross-Encoder)    │  - Query-Document 쌍 입력              
│                     │  - Cross-Attention 기반                
│                     │  - Fine-grained Relevance Score        
└──────────┬──────────┘                                        
           │ Reranked Results                                   
           ▼                                                    
Final Results ◄─────────────────────────────────────────────────
```

---

## 3. 아키텍처 상세

### 3.1 Embedding Model (Bi-Encoder)

| 컴포넌트 | 설명 |
|----------|------|
| **Base Model** | Qwen3-VL Foundation Model |
| **Architecture** | Dual-Tower (Bi-Encoder) |
| **Pooling** | [EOS] Token Hidden State |
| **Output** | Dense Vector (Flexible Dimension) |

**특징**:
- 쿼리와 문서를 독립적으로 인코딩
- 대규모 검색에 효율적 (오프라인 인덱싱 가능)
- Cosine Similarity로 유사도 계산

### 3.2 Reranker Model (Cross-Encoder)

| 컴포넌트 | 설명 |
|----------|------|
| **Base Model** | Qwen3-VL Foundation Model |
| **Architecture** | Cross-Encoder |
| **Mechanism** | Cross-Attention |
| **Output** | Relevance Score (yes/no 토큰 확률) |

**특징**:
- Query-Document 쌍을 함께 처리
- 더 정밀한 관련성 추정
- 초기 검색 결과 재정렬에 사용

### 3.3 Multi-Stage Training Pipeline

```
┌────────────────────────────────────────────────────────────────┐
│ Stage 1: Contrastive Pre-training                              │
│ - 대규모 멀티모달 합성 데이터                                     │
│ - InfoNCE Loss                                                 │
│ - 초기 Cross-Modal Alignment                                   │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Stage 2: Multi-Task Contrastive Learning                       │
│ - 고품질 라벨 데이터                                             │
│ - Embedding + Reranker 동시 학습                               │
│ - Binary Classification Objective (Reranker)                   │
└───────────────────────────┬────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Stage 3: Distillation & Model Merging                          │
│ - Reranker → Embedding Knowledge Distillation                  │
│ - Model Merging for Task Balance                               │
│ - 최종 성능 최적화                                               │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. 벤치마크 성능

### 4.1 MMEB-V2 (Multimodal Embedding Benchmark)

| 모델 | Overall | Image | Video | VisDoc | 비고 |
|------|---------|-------|-------|--------|------|
| **Qwen3-VL-Embedding-8B** | **77.8** | **80.1** | **67.1** | **82.4** | 🥇 SOTA |
| **Qwen3-VL-Embedding-2B** | **73.2** | - | - | - | 경량 모델 |
| RzenEmbed-8B | 72.9 | - | - | - | 오픈소스 |
| VLM2Vec | < 72 | - | - | - | 오픈소스 |
| GME | < 72 | - | - | - | 오픈소스 |
| IFM-TTE (Closed) | 77.9 | - | - | - | 클로즈드 |
| Seed-1.6-embedding | 76.9 | - | - | - | 클로즈드 |

**핵심 성과**:
- MMEB-V2에서 77.8점 달성, 기존 최고 오픈소스 모델 대비 **6.7% 향상**
- 이미지, 비디오, 문서 이미지 **모든 도메인에서 SOTA**
- 2B 모델도 73.2점으로 경쟁력 있는 성능

### 4.2 MMTEB (Text Benchmark)

| 모델 | MMTEB Score | 비고 |
|------|-------------|------|
| Qwen3-Embedding-8B (Text-Only) | **70.58** | MTEB 다국어 1위 |
| Qwen3-VL-Embedding-8B | 약간 낮음 | 멀티모달 특화 |

> **참고**: 순수 텍스트 벤치마크에서는 텍스트 전용 Qwen3-Embedding이 더 높은 성능을 보이지만, Qwen3-VL-Embedding도 경쟁력 있는 수준 유지

### 4.3 Visual Document Retrieval (ViDoRe, JinaVDR)

- ColPali 스타일 모델 대비 우수한 성능
- 문서 이미지 검색에서 82.4점 (VisDoc)
- OCR 없이 문서 이미지 직접 처리 가능

---

## 5. 고급 기능

### 5.1 Matryoshka Representation Learning (MRL)

러시아 인형(마트료시카)처럼 임베딩 차원을 유연하게 조절하는 기술입니다.

```python
# 전체 차원 사용 (고정밀)
embedding_full = model.encode(text, dimension=4096)

# 축소된 차원 사용 (고효율)
embedding_reduced = model.encode(text, dimension=1024)
```

**MRL 장점**:

| 차원 | 용도 | 성능 | 저장 공간 |
|------|------|------|----------|
| 4096D | 고정밀 작업 | 최고 | 기준 |
| 2048D | 일반 검색 | 우수 | 50% 절약 |
| 1024D | 엣지 디바이스 | 양호 | 75% 절약 |
| 512D | 빠른 검색 | 적정 | 87.5% 절약 |

### 5.2 Embedding Quantization

| 양자화 | 성능 유지 | 저장 절약 | 권장 용도 |
|--------|----------|----------|----------|
| FP32 | 100% | 0% | 학습/평가 |
| FP16 | ~99% | 50% | 추론 (권장) |
| INT8 | ~97% | 75% | 대규모 배포 |
| INT4 | ~93% | 87.5% | 엣지 디바이스 |

### 5.3 Instruction-Aware Embedding

작업별 맞춤 지시문을 통해 임베딩 품질을 향상시킬 수 있습니다.

```python
# 작업별 맞춤 지시문 예시
instruction = "Retrieve educational math problems similar to the query"
query = {"text": "삼각형의 넓이를 구하시오", "image": "triangle.png"}

embedding = model.encode(query, instruction=instruction)
```

> **성능 향상**: 지시문 사용 시 대부분의 다운스트림 작업에서 **1-5% 성능 향상**

---

## 6. 다국어 지원

### 6.1 지원 언어

- **30개 이상 언어** 지원 (한국어 포함)
- 다국어, 교차 언어 검색 가능
- 영어 지시문 권장 (학습 데이터 특성)

### 6.2 한국어 적용 고려사항

| 항목 | 상태 | 비고 |
|------|------|------|
| 한국어 텍스트 | ✅ 지원 | 다국어 학습 포함 |
| 한국어 문서 이미지 | ✅ 지원 | OCR-free 처리 |
| 한국어 특화 튜닝 | ⚠️ 미확인 | 파일럿 테스트 필요 |
| 한국어 교육 문항 | ⚠️ 미확인 | 벤치마크 필요 |

---

## 7. 사용 예시

### 7.1 기본 임베딩 생성

```python
from scripts.qwen3_vl_embedding import Qwen3VLEmbedder
import torch

# 모델 초기화
model = Qwen3VLEmbedder(
    model_name_or_path="Qwen/Qwen3-VL-Embedding-2B",
    max_length=8192,
    min_pixels=4096,
    max_pixels=1843200
)

# 문항 임베딩 (텍스트 + 이미지)
queries = [
    {"text": "삼각비를 이용하여 AB의 길이를 구하시오."},
    {"text": "다음 그래프를 해석하시오.", "image": "graph.png"}
]

documents = [
    {"text": "직각삼각형에서 삼각비의 정의..."},
    {"image": "similar_graph.png"}
]

query_embeddings = model.encode(queries)
doc_embeddings = model.encode(documents)

# 유사도 계산
scores = query_embeddings @ doc_embeddings.T
```

### 7.2 Reranker 적용

```python
from scripts.qwen3_vl_reranker import Qwen3VLReranker

reranker = Qwen3VLReranker(
    model_name_or_path="Qwen/Qwen3-VL-Reranker-2B"
)

inputs = {
    "instruction": "Retrieve relevant math problems",
    "query": {"text": "이차방정식의 근을 구하시오"},
    "documents": [
        {"text": "x^2 - 5x + 6 = 0의 해를 구하시오."},
        {"text": "직선의 기울기를 구하시오."},
        {"text": "이차함수의 꼭짓점을 구하시오."}
    ]
}

scores = reranker.score(inputs)
# 예시 결과: [0.92, 0.15, 0.45]
```

### 7.3 vLLM 서버 배포

```bash
# Embedding 서버 실행
vllm serve Qwen/Qwen3-VL-Embedding-2B \
    --task embed \
    --tensor-parallel-size 1

# Reranker 서버 실행
vllm serve Qwen/Qwen3-VL-Reranker-2B \
    --task score \
    --tensor-parallel-size 1
```

### 7.4 End-to-End 멀티모달 RAG 파이프라인

```python
# 공식 GitHub에서 제공하는 E2E RAG 예시 참조
# https://github.com/QwenLM/Qwen3-VL-Embedding/examples/multimodal_rag.py
```

---

## 8. 하드웨어 요구사항

### 8.1 추정 VRAM 요구량

| 모델 | Precision | 예상 VRAM | 권장 GPU |
|------|-----------|----------|----------|
| Qwen3-VL-Embedding-2B | FP16 | ~6-8 GB | RTX 3060 12GB |
| Qwen3-VL-Embedding-2B | INT8 | ~4-5 GB | RTX 3060 12GB |
| Qwen3-VL-Embedding-8B | FP16 | ~18-22 GB | RTX 4090 24GB |
| Qwen3-VL-Embedding-8B | INT8 | ~10-12 GB | RTX 4070 Ti 16GB |

### 8.2 배치 처리 시 고려사항

- 이미지 해상도에 따라 VRAM 사용량 변동
- `min_pixels`, `max_pixels` 파라미터로 조절 가능
- 비디오 처리 시 더 많은 메모리 필요

### 8.3 권장 서버 구성

| 용도 | GPU | 모델 | 예상 처리량 |
|------|-----|------|------------|
| 개발/테스트 | RTX 3060 12GB | 2B (FP16) | ~50 items/sec |
| 프로덕션 (소규모) | RTX 4090 24GB | 8B (FP16) | ~30 items/sec |
| 프로덕션 (대규모) | A100 40GB | 8B (FP16) | ~100 items/sec |

---

## 9. 프로젝트 적용 전략

### 9.1 기존 스택과 비교

| 구분 | 기존 권장 | Qwen3-VL 적용 |
|------|----------|---------------|
| 텍스트 임베딩 | KURE-v1 | Qwen3-VL-Embedding |
| 이미지 임베딩 | SigLIP | Qwen3-VL-Embedding |
| 임베딩 공간 | 별도 (후처리 결합) | **통합** |
| Reranker | 없음 | Qwen3-VL-Reranker |
| 파이프라인 복잡도 | 높음 | **낮음** |
| 모델 수 | 2개 | 1개 (+ Reranker) |

### 9.2 파이프라인 비교

**기존 접근법**:
```
문항 텍스트 → KURE-v1 → 텍스트 벡터 ─┐
                                      ├→ 후처리 결합 → 검색
문항 이미지 → SigLIP → 이미지 벡터 ───┘
```

**Qwen3-VL 적용**:
```
문항 (텍스트+이미지) → Qwen3-VL-Embedding → 단일 벡터 → 검색
                                                        │
                                                        ▼
                                            Qwen3-VL-Reranker
                                                        │
                                                        ▼
                                               최종 결과
```

### 9.3 과목별 적용 전략

| 과목군 | 텍스트 특성 | 이미지 특성 | Qwen3-VL 적용 이점 |
|--------|-------------|-------------|-------------------|
| **수학** | 수식 포함 | 그래프, 도형 | 수식+도형 통합 임베딩 |
| **과학** | 전문 용어 | 실험 장치, 다이어그램 | 텍스트-이미지 의미 연결 |
| **국어** | 긴 지문 | 삽화 (선택적) | 32K 토큰으로 긴 지문 처리 |
| **사회** | 개념 설명 | 지도, 도표, 사진 | 다양한 이미지 유형 통합 |
| **영어** | 영한 혼용 | 삽화, 대화문 | 다국어 + 이미지 통합 |

---

## 10. 권장 의사결정 프로세스

### 10.1 도입 판단 기준

#### ✅ 도입을 권장하는 이유

| 장점 | 프로젝트 영향 |
|------|--------------|
| **단일 모델로 텍스트+이미지 통합** | 파이프라인 복잡도 대폭 감소 (2개 모델 → 1개) |
| **통합 임베딩 공간** | 텍스트-이미지 간 의미적 일관성 보장 |
| **MMEB-V2 77.8점 (SOTA)** | 멀티모달 검색에서 검증된 성능 |
| **Reranker 연계** | 2단계 검색으로 정확도 향상 가능 |
| **MRL 지원** | 차원 조절로 저장/성능 최적화 |
| **Apache 2.0** | 상용 제약 없음 |

#### ⚠️ 고려해야 할 리스크

| 리스크 | 심각도 | 완화 방안 |
|--------|--------|----------|
| **출시 3주차 모델** | 중간 | 파일럿 테스트로 안정성 검증 |
| **한국어 특화 성능 미검증** | 높음 | KURE-v1과 A/B 비교 필수 |
| **순수 텍스트 성능 소폭 저하** | 낮음 | 텍스트 전용 모델 병행 가능 |
| **GPU 요구량 (2B: ~6-8GB)** | 낮음 | 현재 인프라로 충분히 가능 |

### 10.2 의사결정 플로우차트

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 파일럿 테스트 (1주)                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ • 샘플 100건 (과목별 균등 추출)                           ││
│  │ • Qwen3-VL-Embedding-2B vs KURE-v1 + SigLIP 비교        ││
│  │ • 평가 지표: 검색 정확도 (Top-5 Recall), 속도, 메모리     ││
│  └─────────────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: 결과 분석                                           │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ▼                             ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Qwen3-VL이 우수    │     │  KURE+SigLIP이 우수  │
│  (Top-5 Recall 차이 │     │  (Top-5 Recall 차이  │
│   5% 이상 향상)     │     │   5% 미만 또는 저하) │
└──────────┬──────────┘     └──────────┬──────────┘
           │                           │
           ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Step 3A: 본격 도입  │     │  Step 3B: 기존 유지  │
│  ┌─────────────────┐│     │  ┌─────────────────┐│
│  │• 전체 데이터 임베딩││     │  │• KURE+SigLIP 유지││
│  │• Reranker 추가   ││     │  │• 6개월 후 재검토 ││
│  │• 검색 API 개발   ││     │  │• Qwen3-VL 발전   ││
│  │                 ││     │  │  동향 모니터링   ││
│  └─────────────────┘│     └─────────────────────┘
└─────────────────────┘     
```

### 10.3 파일럿 테스트 상세 계획

#### 10.3.1 테스트 데이터셋 구성

| 과목 | 문항 수 | 이미지 포함 | 텍스트 전용 |
|------|---------|------------|------------|
| 수학 | 20건 | 15건 | 5건 |
| 과학 | 20건 | 15건 | 5건 |
| 국어 | 20건 | 5건 | 15건 |
| 사회 | 20건 | 10건 | 10건 |
| 영어 | 20건 | 5건 | 15건 |
| **합계** | **100건** | **50건** | **50건** |

#### 10.3.2 평가 지표

| 지표 | 설명 | 목표 |
|------|------|------|
| **Top-5 Recall** | 상위 5개 검색 결과 내 정답 포함률 | ≥ 85% |
| **Top-10 Recall** | 상위 10개 검색 결과 내 정답 포함률 | ≥ 95% |
| **MRR (Mean Reciprocal Rank)** | 정답의 평균 역순위 | ≥ 0.7 |
| **Latency (P95)** | 95퍼센타일 응답 시간 | ≤ 100ms |
| **VRAM Usage** | GPU 메모리 사용량 | ≤ 12GB |

#### 10.3.3 테스트 시나리오

| 시나리오 | 쿼리 유형 | 기대 결과 |
|----------|----------|----------|
| **S1: 텍스트 → 텍스트** | "이차방정식의 근" | 유사 텍스트 문항 |
| **S2: 텍스트 → 이미지 포함 문항** | "그래프 해석" | 그래프 문항 |
| **S3: 이미지 → 유사 이미지** | 삼각형 도형 이미지 | 유사 도형 문항 |
| **S4: 복합 쿼리** | "다음 그래프에서..." + 이미지 | 유사 복합 문항 |

#### 10.3.4 비교 대상 모델

| 모델 | 역할 | 비고 |
|------|------|------|
| **Qwen3-VL-Embedding-2B** | 멀티모달 통합 | 테스트 대상 |
| **KURE-v1** | 텍스트 임베딩 | 기존 권장 |
| **SigLIP** | 이미지 임베딩 | 기존 권장 |
| **KURE-v1 + SigLIP (결합)** | 후처리 통합 | 비교 기준 |

### 10.4 단계별 도입 전략

| 단계 | 기간 | 내용 | 산출물 |
|------|------|------|--------|
| **Step 1** | 1주 | 환경 구축 + 파일럿 테스트 | 벤치마크 결과 보고서 |
| **Step 2** | 1주 | 결과 분석 + 의사결정 | Go/No-Go 결정 |
| **Step 3A** | 2주 | 전체 데이터 임베딩 | 벡터 DB 구축 |
| **Step 4A** | 1주 | Reranker 통합 | 2단계 검색 파이프라인 |
| **Step 5A** | 1주 | 검색 API 개발 | REST API 배포 |

### 10.5 Go/No-Go 결정 기준

#### ✅ Go 조건 (모두 충족 시)

- [ ] Top-5 Recall이 KURE+SigLIP 대비 **5% 이상 향상**
- [ ] 또는 파이프라인 복잡도 감소로 인한 **개발 비용 30% 이상 절감** 예상
- [ ] VRAM 사용량이 **12GB 이내**
- [ ] P95 Latency가 **100ms 이내**
- [ ] 한국어 문항에서 **치명적 오류 없음**

#### ❌ No-Go 조건 (하나라도 해당 시)

- [ ] Top-5 Recall이 KURE+SigLIP 대비 **5% 이상 저하**
- [ ] 한국어 문항에서 **치명적 오류 발견** (완전히 엉뚱한 결과 등)
- [ ] VRAM 사용량이 **24GB 초과** (8B 모델 기준)
- [ ] 모델 안정성 문제 (크래시, 메모리 누수 등)

### 10.6 롤백 계획

Qwen3-VL 도입 후 문제 발생 시 롤백 절차:

```
┌─────────────────────────────────────────────────────────────┐
│  롤백 트리거 조건                                            │
│  • 프로덕션 검색 정확도 80% 미만                               │
│  • 사용자 불만 급증 (일일 10건 이상)                          │
│  • 시스템 안정성 문제 (가용성 99% 미만)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  롤백 절차 (예상 소요: 2시간)                                  │
│  1. 검색 API 엔드포인트를 KURE+SigLIP 버전으로 전환            │
│  2. KURE+SigLIP 기반 벡터 DB 활성화                          │
│  3. Qwen3-VL 서비스 중지                                     │
│  4. 원인 분석 및 개선 후 재시도                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. 리스크 및 완화 방안

| 리스크 | 영향 | 발생 확률 | 완화 방안 |
|--------|------|----------|----------|
| **신규 모델 (2026.01 출시)** | 안정성 미검증 | 중간 | 파일럿 테스트, 롤백 계획 수립 |
| **한국어 특화 성능 미확인** | 검색 품질 저하 | 높음 | KURE-v1과 A/B 테스트 필수 |
| **GPU 메모리 요구량** | 인프라 비용 | 낮음 | 2B 모델 우선, 양자화 적용 |
| **텍스트 전용 성능 저하** | 국어/영어 문항 | 낮음 | Qwen3-Embedding 병행 검토 |
| **Qwen 팀 지원 중단** | 장기 유지보수 | 낮음 | 오픈소스 포크, 대체 모델 모니터링 |

---

## 12. 결론 및 권장사항

### 12.1 핵심 장점 요약

1. **단일 모델로 멀티모달 통합** → 파이프라인 단순화
2. **SOTA 성능** → MMEB-V2 77.8점 (1위)
3. **Reranker 연계** → 2단계 검색으로 정확도 향상
4. **유연한 차원** → MRL로 효율성/성능 트레이드오프
5. **오픈소스** → Apache 2.0 라이선스

### 12.2 최종 권장 기술 스택

| 컴포넌트 | 1차 권장 | 대안 |
|----------|----------|------|
| **임베딩 모델** | Qwen3-VL-Embedding-2B | 8B (고성능 필요시) |
| **Reranker** | Qwen3-VL-Reranker-2B | 8B (고성능 필요시) |
| **텍스트 전용 fallback** | Qwen3-Embedding | KURE-v1 |
| **벡터 DB** | pgvector (초기) | Qdrant (확장시) |

### 12.3 핵심 질문에 대한 답변

| 질문 | 답변 |
|------|------|
| **도입할 가치가 있는가?** | ✅ 예, 충분히 있습니다 |
| **즉시 전면 도입해야 하는가?** | ⚠️ 아니오, 파일럿 테스트 선행 필요 |
| **가장 큰 이점은?** | 멀티모달 통합으로 파이프라인 단순화 |
| **가장 큰 리스크는?** | 한국어 교육 문항 특화 성능 미검증 |

### 12.4 다음 단계 액션 아이템

| 순서 | 액션 | 담당 | 기한 |
|------|------|------|------|
| 1 | Qwen3-VL-Embedding-2B 환경 구축 | 개발팀 | D+3 |
| 2 | 파일럿 테스트 데이터셋 100건 추출 | 콘텐츠팀 | D+3 |
| 3 | 파일럿 테스트 수행 | 개발팀 | D+7 |
| 4 | 결과 분석 및 Go/No-Go 결정 | TF 전체 | D+10 |
| 5 | (Go 시) 전체 데이터 임베딩 착수 | 개발팀 | D+14 |

---

## 13. 참고 문헌

1. Li, Mingxin et al. (2026). "Qwen3-VL-Embedding and Qwen3-VL-Reranker: A Unified Framework for State-of-the-Art Multimodal Retrieval and Ranking." arXiv:2601.04720. https://arxiv.org/abs/2601.04720

2. Qwen Team (2025). "Qwen3-VL Technical Report." arXiv:2511.21631. https://arxiv.org/abs/2511.21631

3. Zhang, Yanzhao et al. (2025). "Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models." arXiv:2506.05176. https://arxiv.org/abs/2506.05176

4. Qwen Official Blog - Qwen3-VL-Embedding. https://qwen.ai/blog?id=qwen3-vl-embedding

5. GitHub Repository - QwenLM/Qwen3-VL-Embedding. https://github.com/QwenLM/Qwen3-VL-Embedding

6. Hugging Face Model Card - Qwen3-VL-Embedding-2B. https://huggingface.co/Qwen/Qwen3-VL-Embedding-2B

7. Hugging Face Model Card - Qwen3-VL-Embedding-8B. https://huggingface.co/Qwen/Qwen3-VL-Embedding-8B

---

## 문서 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0.0 | 2026-01-27 | 최초 작성 | AI TF |

---

**관련 문서**:
- IOSYS-ITEMBANK-AI-001: 프로젝트 마스터 플랜
- IOSYS-ITEMBANK-AI-001-T01: Phase 1 태스크 목록
- IOSYS-ITEMBANK-AI-001-R01: Phase 1 기술 리서치 결과 (기존)