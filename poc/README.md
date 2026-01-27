# Qwen3-VL-Embedding POC

AI 기반 차세대 문항은행 시스템 - Qwen3-VL-Embedding 모델 POC

## 결론: Conditional Go

| 지표 | 목표 | 결과 | 상태 |
|------|------|------|------|
| P95 Latency | ≤200ms | 30.5ms | ✅ |
| VRAM Usage | ≤8GB | 4.3GB | ✅ |
| Stability | 100% | 100% | ✅ |
| Top-5 Recall | ≥80% | 40.4% | ⚠️ |
| MRR | ≥0.65 | 0.74 | ✅ |

## 빠른 시작

### 1. 환경 설정

```bash
cd /mnt/sda/worker/dev_ldm/iosys-generative/poc

# 가상환경 활성화
source .venv/bin/activate

# PostgreSQL + pgvector 실행
docker-compose up -d
```

### 2. 임베딩 생성

```bash
# Qwen3-VL 임베딩
python scripts/generate_qwen_embeddings.py

# KURE-v1 임베딩
python scripts/generate_kure_embeddings.py

# SigLIP 임베딩
python scripts/generate_siglip_embeddings.py

# 결합 임베딩
python scripts/generate_combined_embeddings.py

# pgvector 저장
python scripts/save_to_pgvector.py
```

### 3. 평가 실행

```bash
# 검색 평가
python scripts/evaluate_search.py --model all

# 성능 측정
python scripts/measure_performance.py

# Reranker 평가
python scripts/evaluate_with_reranker.py
```

## 디렉토리 구조

```
poc/
├── config/                 # 설정 파일
│   └── model_config.py
├── data/                   # 테스트 데이터
│   ├── test_items.json     # 테스트 문항 100건
│   └── ground_truth.json   # Ground Truth
├── models/                 # 다운로드된 모델
│   ├── qwen3-vl-embedding-2b/
│   ├── qwen3-vl-reranker-2b/
│   ├── kure-v1/
│   └── siglip-so400m-patch14-384/
├── results/                # 결과 파일
│   ├── *_embeddings.json
│   ├── search_evaluation.json
│   ├── performance_results.json
│   └── reranker_evaluation.json
├── scripts/                # 실행 스크립트
├── docker-compose.yml      # PostgreSQL + pgvector
├── POC-Report.md          # 최종 보고서
├── HANDOVER.md            # 인수인계 문서
└── README.md              # 본 문서
```

## 데이터베이스

```bash
# 접속 정보
Host: localhost
Port: 5433
Database: poc_itembank
User: poc_user
Password: poc_password

# 테이블 확인
docker exec -it poc-pgvector psql -U poc_user -d poc_itembank -c "\dt"
```

| 테이블 | 행 수 | 설명 |
|--------|------|------|
| qwen_embeddings | 100 | Qwen3-VL 임베딩 (2048차원) |
| kure_embeddings | 100 | KURE-v1 임베딩 (1024차원) |
| siglip_embeddings | 100 | SigLIP 임베딩 (768차원) |
| combined_embeddings | 100 | 결합 임베딩 (1792차원) |
| test_items | 100 | 테스트 문항 메타데이터 |
| ground_truth | 500 | Ground Truth 쌍 |

## 모델 비교 결과

| 모델 | Top-5 | Top-10 | MRR | VRAM |
|------|-------|--------|-----|------|
| **Qwen3-VL-Embedding-2B** | **40.4%** | **51.4%** | 73.8% | 4.3GB |
| KURE-v1 | 33.4% | 48.0% | 73.9% | 2.1GB |
| SigLIP | 13.8% | 21.8% | 27.9% | 1.5GB |
| KURE+SigLIP | 33.0% | 44.8% | 71.7% | 3.6GB |

## 관련 문서

- [POC 최종 보고서](POC-Report.md)
- [인수인계 문서](HANDOVER.md)
- [프로젝트 마스터 플랜](../docs/01%20IOSYS-ITEMBANK-AI-001.md)
- [POC 계획서](../docs/06%20IOSYS-ITEMBANK-AI-001-POC-Qwen3-VL-Embedding.md)

## 다음 단계

1. 수동 Ground Truth 라벨링 (50-100개)
2. 다른 과목 데이터 추가 테스트
3. 멀티모달 Reranker 적용
4. 프로덕션 환경 테스트 (10,952건)
