# Vast.ai 8B VL 멀티모달 임베딩 작업 TODO

**작성일**: 2026-01-28
**목표**: 176,443개 문항에 대한 Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성

---

## 저장 형식

| 형식 | 크기 (추정) | 장점 | 단점 |
|------|-------------|------|------|
| JSON | ~7.7GB | 범용, 가독성 | 느림, 큼 |
| **NumPy (.npz)** | **~1.4GB** | **빠름, 간단** | Python 전용 |
| Parquet | ~1.2GB | 압축, 범용 | 추가 라이브러리 |

**선택: NumPy (.npz)** - JSON 대비 ~5배 압축, 빠른 저장/로드

---

## Phase 1: 로컬 검증 (비용 없음) ✅ 완료

### 1.1 데이터 현황 파악 ✅
- [x] 전체 문항 수 확인: `data/processed/items_part01~18.json` (176,443개)
- [x] has_image=True 문항 수 확인: 45,368개
- [x] 이미지 zip 파일 목록 확인: `data/raw/*.zip`

### 1.2 이미지 데이터 검증 ✅
- [x] quizdata.zip 압축 해제
- [x] 폴더 구조 확인 (218개 YYYYMMDD / 12개 YYYY)
- [x] 총 이미지 파일 수 카운트: 62,658개 (35,198 PNG + 27,460 JPG)

### 1.3 매칭률 검증 ✅
- [x] has_image=True 문항과 실제 이미지 매칭 테스트
- [x] 매칭 실패 문항 원인 분석
  - 과목별: 과학(1,600), 사회(689), 수학 2015(600), 수학(496)
  - 연도별: 2017(1,145), 2011(531), 2005(472)
- [x] **결과: 91.1% 매칭 (41,322/45,368), 4,046개 텍스트 전용 처리**

### 1.4 누락 이미지 해결 ✅
- [x] 추가 이미지 zip 파일 확인: 없음
- [x] 결정: 91.1% 매칭으로 진행, 누락분은 텍스트 전용 처리

### 1.5 업로드 데이터 패키징 ✅
- [x] 검증 완료된 이미지 zip 준비: quizdata.zip (~2.9GB)
- [x] items_part01~18.json 준비 (~262MB)
- [x] 스크립트 파일 준비 (수정 완료)

---

## Phase 2: 스크립트 준비 (로컬) ✅ 완료

### 2.1 validate_image_data.py 수정 ✅
- [x] 18개 파트 파일 로드 지원
- [x] 로컬/Vast.ai 경로 자동 감지
- [x] 검증 결과 JSON 출력

### 2.2 vastai_8b_vl_multimodal.py 수정 ✅
- [x] 18개 파트 파일 로드 지원
- [x] 체크포인트 저장 간격 설정 (500개)
- [x] 메모리 최적화 확인
- [x] **NumPy (.npz) 저장 형식 적용**

### 2.3 로컬 테스트 (샘플)
- [ ] 소규모 샘플(100개)로 스크립트 동작 확인
- [ ] 이미지 로드 및 임베딩 생성 테스트
- [ ] 출력 파일 형식 확인

---

## Phase 3: Vast.ai 실행

### 3.1 인스턴스 준비
- [ ] GPU 선택: RTX 4090 24GB 이상
- [ ] 디스크: 50GB
- [ ] 인스턴스 생성 및 SSH 접속 확인

### 3.2 환경 확인
```bash
nvidia-smi
python3 --version
pip list | grep -E "torch|transformers"
```

### 3.3 데이터 업로드 (로컬과 동일한 구조 유지)
- [ ] 폴더 구조 생성: `mkdir -p data/raw data/processed poc/scripts`
- [ ] quizdata.zip 업로드 → `data/raw/` (~2.9GB)
- [ ] items_part01~18.json 업로드 → `data/processed/` (~262MB)
- [ ] 스크립트 파일 업로드 → `poc/scripts/`

```bash
# Vast.ai에서 폴더 구조 생성
ssh -p {PORT} root@{HOST} "mkdir -p data/raw data/processed poc/scripts"

# 로컬에서 업로드
scp -P {PORT} -i ~/.ssh/id_ed25519_vastai \
    data/raw/quizdata.zip root@{HOST}:~/data/raw/

scp -P {PORT} -i ~/.ssh/id_ed25519_vastai \
    data/processed/items_part*.json root@{HOST}:~/data/processed/

scp -P {PORT} -i ~/.ssh/id_ed25519_vastai \
    poc/scripts/vastai_8b_vl_multimodal.py \
    poc/scripts/validate_image_data.py \
    root@{HOST}:~/poc/scripts/
```

### 3.4 이미지 압축 해제 (로컬과 동일한 경로)
```bash
# Vast.ai에서 실행
cd ~/data/raw
unzip -q quizdata.zip
rm quizdata.zip  # 공간 확보

# 결과: ~/data/raw/{YYYYMMDD}/, ~/data/raw/{YYYY}/{MM}/{DD}/
# 로컬의 data/raw/ 구조와 동일
```

### 3.5 데이터 검증 (로컬과 동일 결과 확인)
```bash
cd ~
python3 poc/scripts/validate_image_data.py
# 예상 결과: 로컬 검증과 동일한 매칭률
```

### 3.6 임베딩 생성 실행
```bash
# 의존성 설치
pip install torch transformers accelerate pillow tqdm qwen-vl-utils

# 실행 (프로젝트 루트에서)
cd ~
python3 poc/scripts/vastai_8b_vl_multimodal.py
```

### 3.7 결과 다운로드
```bash
# 로컬에서 실행 (.npz 형식, ~1.4GB 예상)
scp -P {PORT} -i ~/.ssh/id_ed25519_vastai \
    root@{HOST}:~/poc/results/qwen_vl_embeddings_full_8b_multimodal.npz \
    poc/results/
```

### 3.8 인스턴스 종료
- [ ] 결과 파일 다운로드 확인
- [ ] 인스턴스 중지/삭제

---

## Phase 4: 결과 검증 및 평가

### 4.1 임베딩 파일 검증
- [ ] 파일 크기 확인 (~1.4GB .npz)
- [ ] 임베딩 개수 확인 (176,443개)
- [ ] 임베딩 차원 확인 (4096)
- [ ] 이미지 포함 임베딩 수 확인

```python
# .npz 파일 로드 및 검증 예시
import numpy as np
import json

data = np.load("qwen_vl_embeddings_full_8b_multimodal.npz", allow_pickle=True)
item_ids = data['item_ids']
embeddings = data['embeddings']
metadata = json.loads(data['metadata'][0])

print(f"임베딩 수: {len(item_ids)}")
print(f"임베딩 차원: {embeddings.shape[1]}")
print(f"메타데이터: {metadata}")
```

### 4.2 성능 평가
- [ ] Ground Truth 기준 평가 실행
- [ ] 2B 멀티모달과 비교
- [ ] 결과 문서화

---

## 체크리스트

### 로컬 검증 완료 조건 ✅
- [x] 이미지 매칭률 91.1% (누락 원인 명확화 완료)
- [ ] 스크립트 로컬 테스트 (8B 모델은 로컬 GPU 메모리 부족으로 생략 가능)
- [x] 업로드 파일 목록 확정

### Vast.ai 진행 조건 ✅
- [x] 로컬 검증 완료
- [x] 예상 소요 시간: ~6시간 (176,443개 × 0.12초/개)
- [x] 예상 비용: ~$3 (RTX 4090 $0.50/hr × 6hr)

---

## 현재 상태

| 항목 | 상태 | 비고 |
|------|------|------|
| Phase 1: 로컬 검증 | ✅ 완료 | 매칭률 91.1% (41,322/45,368) |
| Phase 2: 스크립트 수정 | ✅ 완료 | NumPy (.npz) 형식, 18개 파트 지원 |
| Phase 3: Vast.ai 실행 | ✅ 완료 | RTX 4090, 8시간 55분, ~$4.5 |
| Phase 4.1: 파일 검증 | ✅ 완료 | 176,443개 임베딩, NaN/Inf 없음 |
| Phase 4.2: 성능 평가 | ✅ 완료 | **8B VL < 2B**: 2B 유지 권장 |

### 검증 결과 상세
- 총 문항: 176,443개
- has_image=True: 45,368개
- 이미지 매칭 성공: 41,322개 (91.1%)
- 이미지 매칭 실패: 4,046개 (텍스트 전용 처리)

### 출력 파일 정보
- 파일명: `qwen_vl_embeddings_full_8b_multimodal.npz`
- 파일 크기: **2.5GB**
- 임베딩 차원: 4096
- 임베딩 수: 176,443개
- Norm: 1.0 (정규화됨)

### 실행 결과 (2026-01-29)
- 소요 시간: 8시간 55분 (535.4분)
- 처리 속도: 5.49 items/sec
- 이미지 포함: 41,322개
- 에러: 0개
- 총 비용: ~$4.5

---

## 다음 작업

1. ~~**Phase 4.2: 성능 평가**~~ ✅ 완료
   - 결론: **8B VL < 2B Multimodal**
   - Image GT: 8B(92.6%) < 2B(100.0%) -7.4%p
   - Hybrid GT: 8B(70.5%) < 2B(83.6%) -13.1%p
   - **권장: 2B Multimodal 유지, 8B 재생성 불필요**

2. **pgvector 저장**
   - **2B 멀티모달** 176,443건 임베딩 PostgreSQL 저장
   - 대규모 검색 성능 테스트

3. **프로덕션 API 개발**
