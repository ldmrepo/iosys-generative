# Vast.ai GPU 클라우드 사용 가이드

**문서 ID**: IOSYS-ITEMBANK-AI-001-VASTAI-GUIDE
**작성일**: 2026-01-28
**목적**: Qwen3-VL-Embedding-8B 모델 실험을 위한 Vast.ai 환경 설정

---

## 1. 개요

### 1.1 목적
- 로컬 RTX 2070 SUPER (8GB)로 실행 불가한 8B 모델 테스트
- Vast.ai RTX 3090 (24GB) 환경에서 성능 검증

### 1.2 예상 성능 향상

| Metric | 2B (현재) | 8B (예상) | 변화 |
|--------|----------|-----------|------|
| MMEB-V2 Overall | 73.4 | 77.9 | +4.5점 |
| Image GT Top-5 | 76.3% | ~80-82% | +4~6%p |

### 1.3 예상 비용

| 항목 | 값 |
|------|-----|
| GPU | RTX 3090 (24GB) |
| 시간당 비용 | ~$0.20-0.35 |
| 예상 총 비용 | ~$0.15-0.30 |

---

## 2. 사전 준비

### 2.1 SSH 키 생성 (로컬)

```bash
# SSH 키가 없는 경우 생성
ssh-keygen -t ed25519 -C "vastai" -f ~/.ssh/id_ed25519 -N ""

# 공개키 확인 (Vast.ai에 등록할 키)
cat ~/.ssh/id_ed25519.pub
```

**현재 생성된 공개키:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHUq6QrcgE3kQivaPjve1xHj4nNm+Uf+M//+eiC9U2gY iosys-vastai
```

### 2.2 필요한 로컬 파일

```
/mnt/sda/worker/dev_ldm/iosys-generative/
├── poc/
│   ├── data/
│   │   ├── test_items.json              # 테스트 문항 100건
│   │   └── ground_truth_image.json      # Image GT
│   └── scripts/
│       └── generate_qwen_embeddings.py  # 참조용
└── data/
    └── 수학_preprocessed/               # 이미지 파일들
```

---

## 3. Vast.ai 계정 설정

### 3.1 회원가입

1. https://vast.ai 접속
2. **Sign Up** 클릭
3. 이메일/비밀번호 입력
4. 이메일 인증 완료

### 3.2 SSH 키 등록

1. https://cloud.vast.ai/account/ 접속
2. **Manage Keys** → **SSH Keys** 탭
3. 공개키 전체 붙여넣기:
   ```
   ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHUq6QrcgE3kQivaPjve1xHj4nNm+Uf+M//+eiC9U2gY iosys-vastai
   ```
4. **Add SSH Key** 클릭

### 3.3 크레딧 충전

1. **Billing** 탭 접속
2. **Add Credit** 클릭
3. 최소 **$10** 충전 (PayPal/카드)

---

## 4. GPU 인스턴스 선택

### 4.1 검색 페이지

https://cloud.vast.ai/?gpu_option=RTX+3090

### 4.2 필터 설정 (권장)

| 필터 | 권장값 | 이유 |
|------|--------|------|
| GPU Type | RTX 3090 | 24GB VRAM |
| GPU RAM | ≥ 24GB | 8B 모델 필수 |
| Disk Space | ≥ 50GB | 모델 + 데이터 |
| Internet Up | ≥ 100 Mbps | 빠른 업로드 |
| Internet Down | ≥ 200 Mbps | 모델 다운로드 |

### 4.3 인스턴스 선택 기준

| 항목 | 권장값 | 설명 |
|------|--------|------|
| $/hr | $0.20-0.35 | 비용 효율 |
| DLPerf | 높을수록 좋음 | 딥러닝 성능 지표 |
| Reliability | 99%+ | 안정성 |
| Rating | ⭐ 4.5+ | 사용자 평점 |
| Max Duration | ≥ 2시간 | 충분한 작업 시간 |

---

## 5. 인스턴스 대여

### 5.1 템플릿 선택

1. 원하는 인스턴스 행 클릭
2. **RENT** 버튼 클릭
3. 설정:
   - **Image**: `pytorch/pytorch:2.1.0-cuda12.1-cudnn8-devel` (또는 기본 PyTorch)
   - **Disk Space**: `50 GB`
   - **Docker Options**: 기본값 유지

### 5.2 대여 확정

1. **RENT** 버튼 클릭
2. 인스턴스 시작 대기 (1-3분)
3. **Instances** 탭에서 상태 확인: `running`

---

## 6. 인스턴스 접속

### 6.1 SSH 정보 확인

1. **Instances** 탭 접속
2. 실행 중인 인스턴스에서 **Connect** 버튼 클릭
3. SSH 명령어 복사

### 6.2 SSH 접속

```bash
# 예시 (실제 IP/PORT는 Vast.ai에서 확인)
ssh -p <PORT> root@<IP_ADDRESS>

# 예: ssh -p 12345 root@123.456.789.10
```

### 6.3 Jupyter 접속 (대안)

- **Instances** → **Open** 버튼 → Jupyter Lab 열림
- 브라우저에서 직접 코드 실행 가능

---

## 7. 환경 설정 (인스턴스 내부)

### 7.1 기본 설정

```bash
# 작업 디렉토리 생성
mkdir -p /workspace/poc/data
mkdir -p /workspace/poc/results
mkdir -p /workspace/data
cd /workspace/poc

# pip 업그레이드
pip install --upgrade pip
```

### 7.2 필수 패키지 설치

```bash
# PyTorch 및 기본 패키지
pip install torch transformers accelerate

# Qwen VL 관련
pip install qwen-vl-utils pillow tqdm

# Flash Attention (속도 최적화)
pip install flash-attn --no-build-isolation
```

### 7.3 설치 확인

```bash
python -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA Available: {torch.cuda.is_available()}')
print(f'GPU: {torch.cuda.get_device_name(0)}')
print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB')
"
```

**예상 출력:**
```
PyTorch: 2.x.x
CUDA Available: True
GPU: NVIDIA GeForce RTX 3090
VRAM: 24.0GB
```

---

## 8. 데이터 업로드

### 8.1 환경 변수 설정 (로컬)

```bash
# Vast.ai 접속 정보 (실제 값으로 대체)
export VAST_HOST="root@<IP_ADDRESS>"
export VAST_PORT="<PORT>"

# 예:
# export VAST_HOST="root@123.456.789.10"
# export VAST_PORT="12345"
```

### 8.2 테스트 데이터 업로드

```bash
# 테스트 문항
scp -P $VAST_PORT \
    /mnt/sda/worker/dev_ldm/iosys-generative/poc/data/test_items.json \
    $VAST_HOST:/workspace/poc/data/

# Ground Truth
scp -P $VAST_PORT \
    /mnt/sda/worker/dev_ldm/iosys-generative/poc/data/ground_truth_image.json \
    $VAST_HOST:/workspace/poc/data/
```

### 8.3 이미지 폴더 업로드 (멀티모달 테스트 시)

```bash
# 이미지 폴더 전체 (시간 소요)
scp -r -P $VAST_PORT \
    /mnt/sda/worker/dev_ldm/iosys-generative/data/수학_preprocessed \
    $VAST_HOST:/workspace/data/
```

---

## 9. 8B 모델 임베딩 생성

### 9.1 스크립트 생성 (인스턴스 내부)

```bash
cat > /workspace/poc/generate_8b_embeddings.py << 'SCRIPT_EOF'
#!/usr/bin/env python3
"""
Qwen3-VL-Embedding-8B 임베딩 생성 스크립트
Vast.ai RTX 3090 환경용
"""

import torch
import json
from pathlib import Path
from tqdm import tqdm
from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

def main():
    # 설정
    MODEL_NAME = "Qwen/Qwen3-VL-Embedding-8B"
    DATA_PATH = "/workspace/poc/data/test_items.json"
    OUTPUT_PATH = "/workspace/poc/results/qwen_embeddings_8b.json"

    # 모델 로드
    print("=" * 50)
    print("Loading Qwen3-VL-Embedding-8B...")
    print("=" * 50)

    model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
        device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(MODEL_NAME)

    print(f"Model loaded successfully!")
    print(f"VRAM Usage: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print()

    # 테스트 데이터 로드
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"Loaded {len(items)} items")
    print()

    # 임베딩 생성
    embeddings = {}

    print("Generating embeddings...")
    for item in tqdm(items, desc="Embedding"):
        item_id = item["item_id"]

        # 텍스트 결합
        question_text = item.get("question_text", "")
        explanation_text = item.get("explanation_text", "")
        text = f"{question_text} {explanation_text}".strip()

        if not text:
            continue

        # 임베딩 생성
        inputs = processor(
            text=text,
            return_tensors="pt",
            truncation=True,
            max_length=8192
        ).to(model.device)

        with torch.no_grad():
            outputs = model(**inputs, output_hidden_states=True)
            # Mean pooling
            hidden_states = outputs.hidden_states[-1]
            attention_mask = inputs["attention_mask"]

            # Mask padding tokens
            mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
            sum_embeddings = torch.sum(hidden_states * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            embedding = (sum_embeddings / sum_mask).squeeze().cpu().numpy().tolist()

        embeddings[item_id] = {
            "embedding": embedding,
            "dim": len(embedding)
        }

    # 결과 저장
    result = {
        "model": MODEL_NAME,
        "num_items": len(embeddings),
        "embedding_dim": len(next(iter(embeddings.values()))["embedding"]),
        "embeddings": embeddings
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 50)
    print(f"Done! Saved {len(embeddings)} embeddings")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Embedding dimension: {result['embedding_dim']}")
    print(f"Final VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("=" * 50)

if __name__ == "__main__":
    main()
SCRIPT_EOF

chmod +x /workspace/poc/generate_8b_embeddings.py
```

### 9.2 스크립트 실행

```bash
cd /workspace/poc
python generate_8b_embeddings.py
```

### 9.3 예상 출력

```
==================================================
Loading Qwen3-VL-Embedding-8B...
==================================================
Model loaded successfully!
VRAM Usage: 16.XX GB

Loaded 100 items

Generating embeddings...
Embedding: 100%|██████████| 100/100 [XX:XX<00:00]

==================================================
Done! Saved 100 embeddings
Output: /workspace/poc/results/qwen_embeddings_8b.json
Embedding dimension: 4096
Final VRAM: 17.XX GB
==================================================
```

---

## 10. 결과 다운로드

### 10.1 임베딩 결과 다운로드 (로컬)

```bash
scp -P $VAST_PORT \
    $VAST_HOST:/workspace/poc/results/qwen_embeddings_8b.json \
    /mnt/sda/worker/dev_ldm/iosys-generative/poc/results/
```

### 10.2 다운로드 확인

```bash
ls -la /mnt/sda/worker/dev_ldm/iosys-generative/poc/results/qwen_embeddings_8b.json
```

---

## 11. 인스턴스 종료 (중요!)

### 11.1 종료 방법

1. https://cloud.vast.ai/instances/ 접속
2. 인스턴스 행에서 **Destroy** 버튼 클릭
3. 확인 대화상자에서 **OK**

### 11.2 확인

- 인스턴스 목록에서 해당 인스턴스 사라짐
- **Billing** 탭에서 사용량 확인

⚠️ **주의**: 종료하지 않으면 계속 과금됩니다!

---

## 12. 로컬에서 성능 평가

### 12.1 평가 스크립트 실행

```bash
cd /mnt/sda/worker/dev_ldm/iosys-generative/poc
source .venv/bin/activate

# 8B 임베딩으로 평가 (스크립트 수정 필요)
python scripts/evaluate_search.py --embeddings results/qwen_embeddings_8b.json
```

### 12.2 2B vs 8B 비교

```python
# 비교 분석 예시
import json

with open("results/qwen_embeddings_multimodal_meanpool.json") as f:
    results_2b = json.load(f)

with open("results/qwen_embeddings_8b.json") as f:
    results_8b = json.load(f)

print(f"2B embedding dim: {results_2b.get('embedding_dim', 2048)}")
print(f"8B embedding dim: {results_8b.get('embedding_dim', 4096)}")
```

---

## 13. 문제 해결

### 13.1 SSH 접속 실패

```bash
# 권한 확인
chmod 600 ~/.ssh/id_ed25519

# verbose 모드로 디버깅
ssh -v -p <PORT> root@<IP>
```

### 13.2 VRAM 부족

```bash
# GPU 메모리 상태 확인
nvidia-smi

# 메모리 정리
python -c "import torch; torch.cuda.empty_cache()"
```

### 13.3 패키지 설치 실패

```bash
# pip 캐시 정리
pip cache purge

# 재설치
pip install --no-cache-dir <package>
```

### 13.4 모델 다운로드 느림

```bash
# HuggingFace 미러 사용
export HF_ENDPOINT=https://hf-mirror.com
```

---

## 14. 빠른 참조

### 14.1 주요 명령어

```bash
# SSH 접속
ssh -p <PORT> root@<IP>

# 파일 업로드
scp -P <PORT> local_file root@<IP>:/workspace/

# 파일 다운로드
scp -P <PORT> root@<IP>:/workspace/file ./

# 폴더 업로드
scp -r -P <PORT> local_folder root@<IP>:/workspace/

# GPU 상태
nvidia-smi

# VRAM 사용량 (Python)
python -c "import torch; print(f'{torch.cuda.memory_allocated()/1e9:.2f}GB')"
```

### 14.2 유용한 링크

| 링크 | 설명 |
|------|------|
| https://cloud.vast.ai | Vast.ai 콘솔 |
| https://cloud.vast.ai/instances/ | 인스턴스 관리 |
| https://cloud.vast.ai/account/ | 계정/SSH키 설정 |
| https://cloud.vast.ai/billing/ | 비용 확인 |

### 14.3 비용 계산

| 작업 | 예상 시간 | 비용 ($0.25/hr 기준) |
|------|----------|---------------------|
| 환경 설정 | 10분 | $0.04 |
| 데이터 업로드 | 5분 | $0.02 |
| 임베딩 생성 (100건) | 10분 | $0.04 |
| 결과 다운로드 | 2분 | $0.01 |
| **총계** | **~30분** | **~$0.12** |

---

## 문서 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| v1.0.0 | 2026-01-28 | 최초 작성 |
