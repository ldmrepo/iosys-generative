# IOSYS ItemBank AI

AI 기반 차세대 문항은행 시스템

## 프로젝트 개요

교육 콘텐츠(문항)의 멀티모달 임베딩 기반 검색, 자동 분류, 이미지 참조형 문항 생성을 위한 AI 시스템

### 핵심 기능

| 기능 | 설명 | 상태 |
|------|------|------|
| 자연어 문항 검색 | 의미 기반 유사 문항 검색 | POC 완료 |
| 유사 문항 추천 | 멀티모달 임베딩 기반 추천 | POC 완료 |
| 자동 분류 | 교육과정/성취기준/난이도 분류 | 예정 |
| 이미지 문항 생성 | Fact Graph 기반 환각 방지 생성 | 예정 |

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      Client / API                           │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Retrieval Pipeline                        │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ Qwen3-VL-       │───▶│ Qwen3-VL-       │                 │
│  │ Embedding-2B    │    │ Reranker-2B     │                 │
│  │ (Initial Search)│    │ (Precision)     │                 │
│  └─────────────────┘    └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Vector Database                           │
│                    (pgvector / Qdrant)                       │
└─────────────────────────────────────────────────────────────┘
```

## 디렉토리 구조

```
iosys-generative/
├── data/                           # 원본 데이터
│   └── 수학_preprocessed/          # 전처리된 수학 문항 (10,952건)
├── docs/                           # 프로젝트 문서
│   ├── 01 IOSYS-ITEMBANK-AI-001.md           # 마스터 플랜
│   ├── 02 ...-T01.md                         # Phase 1 태스크
│   ├── 04 ...-R01.md                         # 기술 리서치
│   ├── 05 ...-R02.md                         # Qwen3-VL 리서치
│   └── 06 ...-POC-Qwen3-VL-Embedding.md      # POC 계획서
├── poc/                            # POC 구현
│   ├── config/                     # 설정 파일
│   ├── data/                       # 테스트 데이터
│   ├── models/                     # 다운로드된 모델 (gitignore)
│   ├── results/                    # 실험 결과
│   ├── scripts/                    # 실행 스크립트
│   ├── POC-Report.md              # POC 최종 보고서
│   └── HANDOVER.md                # 인수인계 문서
├── preprocessing/                  # 전처리 파이프라인
│   └── run_preprocess.py
└── CLAUDE.md                       # AI 어시스턴트 지침
```

## 기술 스택

### AI 모델

| 모델 | 용도 | 크기 | 차원 |
|------|------|------|------|
| Qwen3-VL-Embedding-2B | 멀티모달 임베딩 | 4GB | 2048 |
| Qwen3-VL-Reranker-2B | 재순위화 | 4GB | - |
| KURE-v1 | 한국어 텍스트 임베딩 | 2.2GB | 1024 |
| SigLIP | 이미지 임베딩 | 1.5GB | 768 |

### 인프라

| 구성요소 | 기술 |
|----------|------|
| Vector DB | PostgreSQL + pgvector (초기), Qdrant (확장) |
| Runtime | Python 3.11, PyTorch 2.5, Transformers 5.0 |
| Container | Docker Compose |

## 빠른 시작

### 요구사항

- GPU: NVIDIA RTX 2070 8GB 이상
- RAM: 32GB 이상
- Storage: 50GB 이상

### 설치

```bash
# 저장소 클론
git clone https://github.com/ldmrepo/iosys-generative.git
cd iosys-generative

# POC 환경 설정
cd poc
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# PostgreSQL + pgvector 실행
docker-compose up -d

# 모델 다운로드 (별도 실행 필요)
python scripts/test_model_load.py
```

### 실행

```bash
# 임베딩 생성
python scripts/generate_qwen_embeddings.py

# 검색 평가
python scripts/evaluate_search.py --model all

# 성능 측정
python scripts/measure_performance.py
```

## POC 결과 요약

**결론: Conditional Go** ⚠️

| 지표 | 목표 | 결과 | 상태 |
|------|------|------|------|
| P95 Latency | ≤200ms | 30.5ms | ✅ |
| VRAM Usage | ≤8GB | 4.3GB | ✅ |
| Stability | 100% | 100% | ✅ |
| Top-5 Recall | ≥80% | 40.4% | ⚠️ |
| MRR | ≥0.65 | 0.74 | ✅ |

> Top-K Recall 미달은 자동 생성된 Ground Truth의 한계로 판단됨

자세한 내용: [POC 보고서](poc/POC-Report.md)

## 로드맵

### Phase 1: 문항 벡터화 및 검색 (현재)
- [x] Qwen3-VL-Embedding POC
- [x] pgvector 연동
- [x] Reranker 적용 검증
- [ ] 수동 Ground Truth 라벨링
- [ ] 전체 데이터(10,952건) 임베딩

### Phase 2: 자동 분류 시스템
- [ ] 교육과정 분류 모델
- [ ] 성취기준 매핑
- [ ] 난이도 예측

### Phase 3: 이미지 문항 생성
- [ ] Fact Graph 추출 파이프라인
- [ ] 문항 생성 모델
- [ ] Integrity Gate 검증

### Phase 4: 통합 플랫폼
- [ ] REST API 개발
- [ ] 관리자 UI
- [ ] 모니터링 대시보드

## 문서

| 문서 | 설명 |
|------|------|
| [마스터 플랜](docs/01%20IOSYS-ITEMBANK-AI-001.md) | 프로젝트 전체 계획 |
| [POC 보고서](poc/POC-Report.md) | POC 최종 결과 |
| [인수인계 문서](poc/HANDOVER.md) | 작업 이력 및 가이드 |
| [POC README](poc/README.md) | POC 실행 가이드 |

## 라이선스

Private - IOSYS Internal Use Only
