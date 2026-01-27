# POC 작업 인수인계 문서

**문서 ID**: IOSYS-ITEMBANK-AI-001-HANDOVER
**작성일**: 2026-01-27
**프로젝트**: AI 기반 차세대 문항은행 시스템 - Qwen3-VL-Embedding POC

---

## 1. 프로젝트 개요

### 1.1 목적
Qwen3-VL-Embedding-2B 모델을 사용하여 수학 문항의 멀티모달(텍스트+이미지) 임베딩 및 유사 문항 검색 성능을 검증하는 POC(Proof of Concept) 수행.

### 1.2 최종 결론
**Conditional Go** ⚠️
- 시스템 성능 요구사항 모두 충족
- 검색 정확도는 목표 미달이나 Ground Truth 품질 이슈로 판단
- Qwen3-VL이 기존 모델 조합(KURE+SigLIP) 대비 우수

---

## 2. 시스템 환경

### 2.1 하드웨어

| 구성 요소 | 사양 |
|----------|------|
| GPU | NVIDIA GeForce RTX 2070 SUPER 8GB |
| CPU | Intel i7-11700KF (8코어/16스레드) |
| RAM | 64GB DDR4 |
| Storage | /mnt/sda (125GB 여유) |

### 2.2 소프트웨어

| 구성 요소 | 버전 |
|----------|------|
| OS | Ubuntu Linux 6.8.0-90-generic |
| Python | 3.11.13 |
| PyTorch | 2.5.1+cu121 |
| Transformers | 5.0.0 |
| PostgreSQL | 16 (Docker) |
| pgvector | 0.8.1 |

### 2.3 디렉토리 구조

```
/mnt/sda/worker/dev_ldm/iosys-generative/
├── poc/                          # POC 작업 디렉토리
│   ├── .venv/                    # Python 가상환경 (uv 사용)
│   ├── config/                   # 설정 파일
│   │   └── model_config.py       # 모델 및 DB 설정
│   ├── data/                     # 테스트 데이터
│   │   ├── test_items.json       # 테스트 문항 100건
│   │   └── ground_truth.json     # Ground Truth 데이터
│   ├── models/                   # 다운로드된 모델
│   │   ├── qwen3-vl-embedding-2b/   # Qwen3-VL Embedding (4GB)
│   │   ├── qwen3-vl-reranker-2b/    # Qwen3-VL Reranker (4GB)
│   │   ├── kure-v1/                 # KURE-v1 (2.2GB)
│   │   └── siglip-so400m-patch14-384/ # SigLIP (1.5GB)
│   ├── results/                  # 결과 파일
│   │   ├── qwen_embeddings.json
│   │   ├── kure_embeddings.json
│   │   ├── siglip_embeddings.json
│   │   ├── combined_embeddings.json
│   │   ├── search_evaluation.json
│   │   ├── performance_results.json
│   │   └── reranker_evaluation.json
│   ├── scripts/                  # 실행 스크립트
│   ├── docker-compose.yml        # PostgreSQL + pgvector
│   ├── POC-Report.md            # 최종 POC 보고서
│   └── HANDOVER.md              # 본 문서
└── data/
    └── 수학_preprocessed/        # 전처리된 수학 문항 10,952건
```

---

## 3. 환경 설정 방법

### 3.1 HuggingFace 캐시 설정

GPU 메모리 절약을 위해 HF 캐시를 /mnt/sda로 이동함:

```bash
# 심볼릭 링크 확인
ls -la ~/.cache/huggingface
# -> /mnt/sda/cache/huggingface 로 연결됨
```

### 3.2 가상환경 활성화

```bash
cd /mnt/sda/worker/dev_ldm/iosys-generative/poc
source .venv/bin/activate
```

### 3.3 PostgreSQL + pgvector 실행

```bash
cd /mnt/sda/worker/dev_ldm/iosys-generative/poc
docker-compose up -d

# 접속 정보
# Host: localhost
# Port: 5433
# Database: poc_itembank
# User: poc_user
# Password: poc_password
```

### 3.4 데이터베이스 연결 테스트

```bash
docker exec -it poc-pgvector psql -U poc_user -d poc_itembank -c "SELECT COUNT(*) FROM qwen_embeddings;"
# Expected: 100
```

---

## 4. 완료된 태스크 목록

### Phase 1: 환경 구성 (6개 태스크)

| # | 태스크 | 상태 | 설명 |
|---|--------|------|------|
| 1 | 프로젝트 폴더 및 가상환경 구성 | ✅ 완료 | uv로 Python 3.11 가상환경 생성 |
| 2 | Qwen3-VL-Embedding-2B 다운로드 | ✅ 완료 | 4GB, FP16 로드 테스트 성공 (VRAM 4.26GB) |
| 3 | 비교 모델 다운로드 (KURE-v1, SigLIP) | ✅ 완료 | KURE 2.2GB, SigLIP 1.5GB |
| 4 | PostgreSQL + pgvector 설정 | ✅ 완료 | Docker Compose로 설치, Port 5433 |
| 5 | 수학 테스트 데이터 100건 샘플링 | ✅ 완료 | 이미지형 35건, 텍스트형 35건, LaTeX형 30건 |
| 6 | Ground Truth 라벨링 | ✅ 완료 | TF-IDF 기반 자동 생성 500쌍 |

### Phase 2: 임베딩 생성 (6개 태스크)

| # | 태스크 | 상태 | 설명 |
|---|--------|------|------|
| 7 | Qwen3-VL 임베딩 생성 스크립트 작성 | ✅ 완료 | `scripts/generate_qwen_embeddings.py` |
| 8 | Qwen3-VL 임베딩 생성 실행 | ✅ 완료 | 100건, 2048차원, 2.7초 |
| 9 | KURE-v1 텍스트 임베딩 생성 | ✅ 완료 | 100건, 1024차원 |
| 10 | SigLIP 이미지 임베딩 생성 | ✅ 완료 | 100건, 768차원 (이미지 없는 경우 zero vector) |
| 11 | KURE+SigLIP 결합 임베딩 생성 | ✅ 완료 | 100건, 1792차원 (concatenation) |
| 12 | 임베딩 pgvector 저장 | ✅ 완료 | 6개 테이블에 저장 완료 |

### Phase 3: 검색 평가 (7개 태스크)

| # | 태스크 | 상태 | 설명 |
|---|--------|------|------|
| 13 | 검색 평가 스크립트 작성 | ✅ 완료 | `scripts/evaluate_search.py` |
| 14 | Qwen3-VL 검색 테스트 | ✅ 완료 | Top-5: 40.4%, MRR: 73.8% |
| 15 | KURE-v1 검색 테스트 | ✅ 완료 | Top-5: 33.4%, MRR: 73.9% |
| 16 | KURE+SigLIP 결합 검색 테스트 | ✅ 완료 | Top-5: 33.0%, MRR: 71.7% |
| 17 | Qwen3-VL-Reranker 효과 검증 | ✅ 완료 | 별도 태스크로 진행 |
| 18 | 문항 유형별 검색 분석 | ✅ 완료 | 이미지형 > LaTeX형 > 텍스트형 |
| 19 | 오류 케이스 분석 | ✅ 완료 | Ground Truth 품질 이슈 확인 |

### Phase 4: 성능 측정 (5개 태스크)

| # | 태스크 | 상태 | 설명 |
|---|--------|------|------|
| 20 | Latency 측정 스크립트 작성 | ✅ 완료 | `scripts/measure_performance.py` |
| 21 | 단일 쿼리 Latency 측정 | ✅ 완료 | P95: 30.5ms (목표 ≤200ms) ✅ |
| 22 | 배치 처리 Throughput 측정 | ✅ 완료 | 43.2 items/sec |
| 23 | VRAM 사용량 모니터링 | ✅ 완료 | Peak: 4.33GB (목표 ≤8GB) ✅ |
| 24 | 안정성 테스트 (1,000회) | ✅ 완료 | 100% 성공률 ✅ |

### Phase 5: 분석 및 보고 (3개 태스크)

| # | 태스크 | 상태 | 설명 |
|---|--------|------|------|
| 25 | 결과 집계 및 시각화 | ✅ 완료 | 전체 결과 분석 |
| 26 | Go/No-Go 판단 | ✅ 완료 | Conditional Go |
| 27 | POC 최종 보고서 작성 | ✅ 완료 | `POC-Report.md` |

### 추가 태스크: Reranker 적용 (3개 태스크)

| # | 태스크 | 상태 | 설명 |
|---|--------|------|------|
| 28 | Qwen3-VL-Reranker-2B 다운로드 | ✅ 완료 | 4GB, VRAM 4.26GB |
| 29 | Reranker 평가 스크립트 작성 | ✅ 완료 | `scripts/evaluate_with_reranker.py` |
| 30 | Reranker 적용 검색 평가 실행 | ✅ 완료 | Top-10 +4.0%p 향상 |

---

## 5. 주요 스크립트 실행 방법

### 5.1 임베딩 생성

```bash
cd /mnt/sda/worker/dev_ldm/iosys-generative/poc
source .venv/bin/activate

# Qwen3-VL 임베딩 생성
python scripts/generate_qwen_embeddings.py

# KURE-v1 임베딩 생성
python scripts/generate_kure_embeddings.py

# SigLIP 임베딩 생성
python scripts/generate_siglip_embeddings.py

# 결합 임베딩 생성
python scripts/generate_combined_embeddings.py
```

### 5.2 pgvector 저장

```bash
# 모든 임베딩을 PostgreSQL에 저장
python scripts/save_to_pgvector.py
```

### 5.3 검색 평가

```bash
# 전체 모델 평가
python scripts/evaluate_search.py --model all

# 특정 모델만 평가
python scripts/evaluate_search.py --model qwen
```

### 5.4 성능 측정

```bash
python scripts/measure_performance.py
```

### 5.5 Reranker 평가

```bash
python scripts/evaluate_with_reranker.py
```

---

## 6. 핵심 결과 요약

### 6.1 검색 정확도 (모델 비교)

| 모델 | Top-5 Recall | Top-10 Recall | MRR |
|------|--------------|---------------|-----|
| **Qwen3-VL-Embedding-2B** | **40.4%** | **51.4%** | 73.8% |
| KURE-v1 | 33.4% | 48.0% | **73.9%** |
| SigLIP | 13.8% | 21.8% | 27.9% |
| KURE+SigLIP | 33.0% | 44.8% | 71.7% |

### 6.2 시스템 성능

| 지표 | 목표 | 결과 | 상태 |
|------|------|------|------|
| P95 Latency | ≤200ms | 30.5ms | ✅ |
| VRAM Usage | ≤8GB | 4.33GB | ✅ |
| Stability | 100% | 100% | ✅ |

### 6.3 Reranker 적용 효과

| 지표 | Embedding Only | + Reranker | 변화 |
|------|----------------|------------|------|
| Top-5 Recall | 40.4% | 38.8% | -1.6%p |
| Top-10 Recall | 51.4% | 55.4% | **+4.0%p** |
| NDCG@10 | 52.5% | 53.5% | +1.0%p |

---

## 7. 해결된 이슈 및 트러블슈팅

### 7.1 uv pip 환경 문제

**문제**: uv pip가 시스템 Python(anaconda)을 사용
**해결**: `uv pip install --python .venv/bin/python` 옵션 사용

### 7.2 SigLIP 이미지 경로 문제

**문제**: 이미지 경로가 날짜별 중첩 폴더에 위치
**해결**: `subprocess.run(['find', ...])` 사용하여 재귀 검색

### 7.3 SigLIP AutoProcessor 오류

**문제**: `AutoProcessor` 사용 시 NoneType 오류
**해결**: `SiglipImageProcessor` 및 `SiglipModel`로 변경

### 7.4 HuggingFace 캐시 디스크 공간

**문제**: 루트 파티션 공간 부족 (7.3GB)
**해결**: `/mnt/sda/cache/huggingface`로 심볼릭 링크 생성

---

## 8. 다음 단계 권장사항

### 8.1 즉시 수행 필요

1. **수동 Ground Truth 라벨링**
   - 콘텐츠 담당자가 50-100개 문항 직접 라벨링
   - 실제 검색 정확도 재검증

2. **다른 과목 데이터 추가**
   - 과학, 국어, 사회, 영어 데이터 테스트
   - 과목별 성능 편차 확인

### 8.2 중기 개선

1. **멀티모달 Reranker 적용**
   - 이미지 포함 Reranking 구현
   - Top-30 → Rerank → Top-10 파이프라인

2. **프로덕션 환경 테스트**
   - 전체 10,952건 문항 임베딩
   - 실제 부하 테스트

### 8.3 장기 로드맵

1. Qdrant/Milvus로 벡터 DB 마이그레이션
2. API 서버 개발
3. 자동 분류 시스템 연동

---

## 9. 연락처 및 참고 문서

### 9.1 관련 문서

| 문서 | 위치 |
|------|------|
| 프로젝트 마스터 플랜 | `docs/01 IOSYS-ITEMBANK-AI-001.md` |
| POC 계획서 | `docs/06 IOSYS-ITEMBANK-AI-001-POC-Qwen3-VL-Embedding.md` |
| 기술 리서치 보고서 | `docs/05 IOSYS-ITEMBANK-AI-001-R02.md` |
| POC 최종 보고서 | `poc/POC-Report.md` |

### 9.2 외부 참고 자료

- [Qwen3-VL-Embedding GitHub](https://github.com/QwenLM/Qwen3-VL-Embedding)
- [pgvector 문서](https://github.com/pgvector/pgvector)
- [KURE-v1 HuggingFace](https://huggingface.co/nlpai-lab/KURE-v1)

---

## 문서 이력

| 버전 | 일자 | 변경 내용 | 작성자 |
|------|------|----------|--------|
| v1.0.0 | 2026-01-27 | 최초 작성 | AI TF |
