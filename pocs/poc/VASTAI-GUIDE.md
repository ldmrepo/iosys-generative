# Vast.ai GPU 클라우드 사용 가이드

**문서 ID**: IOSYS-ITEMBANK-AI-001-VASTAI-GUIDE
**작성일**: 2026-01-28
**최종 수정**: 2026-01-28
**목적**: Qwen3-Embedding-8B 모델 실험을 위한 Vast.ai 환경 설정

---

## 1. 개요

### 1.1 목적
- 로컬 RTX 2070 SUPER (8GB)로 실행 불가한 8B 모델 테스트
- Vast.ai RTX 3090 Ti (24GB) 환경에서 성능 검증

### 1.2 실제 실험 결과 (2026-01-28)

| 항목 | 값 |
|------|-----|
| 모델 | Qwen3-Embedding-8B |
| GPU | RTX 3090 Ti (24GB) |
| VRAM 사용 | 15.17 GB |
| 임베딩 차원 | 4096 (2B는 2048) |
| 생성 시간 | ~10분 (100건) |
| 총 비용 | ~$0.58 (충전 $5 → 잔액 $4.42) |

### 1.3 비용 정보

| 항목 | 값 |
|------|-----|
| GPU | RTX 3090 Ti |
| 시간당 비용 | ~$0.14-0.15 |
| 실제 사용 비용 | ~$0.58 |

---

## 2. 빠른 실행 가이드 (요약)

전체 과정을 빠르게 실행하려면 아래 순서를 따르세요:

```bash
# 1. SSH 키 생성 (최초 1회)
ssh-keygen -t ed25519 -C "iosys-vastai" -f ~/.ssh/id_ed25519_vastai -N ""
cat ~/.ssh/id_ed25519_vastai.pub  # 이 공개키를 Vast.ai에 등록

# 2. Vast.ai 설정 (웹)
# - https://cloud.vast.ai/account/ → SSH Keys에 공개키 등록
# - https://cloud.vast.ai/billing/ → $5 이상 크레딧 충전
# - https://cloud.vast.ai/templates/ → PyTorch (Vast) 템플릿 선택
# - RTX 3090 Ti 인스턴스 선택, Container Size: 50GB로 설정, RENT

# 3. SSH 접속 (Instances → Connect에서 포트 확인)
ssh -i ~/.ssh/id_ed25519_vastai -p <PORT> root@<IP> -o StrictHostKeyChecking=no

# 4. 환경 설정 (인스턴스 내부)
source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base
pip install torch transformers accelerate tqdm -q
mkdir -p /workspace/poc/data /workspace/poc/results

# 5. 데이터 업로드 (로컬에서)
scp -i ~/.ssh/id_ed25519_vastai -P <PORT> test_items.json root@<IP>:/workspace/poc/data/

# 6. 스크립트 실행 (인스턴스 내부)
cd /workspace/poc && python generate_8b_embeddings.py

# 7. 결과 다운로드 (로컬에서)
scp -i ~/.ssh/id_ed25519_vastai -P <PORT> root@<IP>:/workspace/poc/results/qwen_embeddings_8b.json ./

# 8. 인스턴스 종료 (웹) - 중요!
# Vast.ai → Instances → Destroy
```

---

## 3. 상세 절차

### 3.1 SSH 키 생성 (로컬, 최초 1회)

```bash
# SSH 키 생성
ssh-keygen -t ed25519 -C "iosys-vastai" -f ~/.ssh/id_ed25519_vastai -N ""

# 공개키 확인 (Vast.ai에 등록할 키)
cat ~/.ssh/id_ed25519_vastai.pub
```

**생성된 공개키 예시:**
```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC7/txvTYUQF6hQxRscEk58iAjwdnMhnvdrNxeQRdSN4 iosys-vastai
```

### 3.2 Vast.ai 계정 설정

#### 3.2.1 회원가입
1. https://vast.ai 접속
2. **Sign Up** 클릭
3. 이메일/비밀번호 입력
4. 이메일 인증 완료

#### 3.2.2 SSH 키 등록
1. https://cloud.vast.ai/account/ 접속
2. **SSH Keys** 탭 클릭
3. 공개키 전체 붙여넣기
4. **Add SSH Key** 클릭

#### 3.2.3 크레딧 충전
1. https://cloud.vast.ai/billing/ 접속
2. **Add Credit** 클릭
3. **$5** 선택 (최소 금액, 실험에 충분)
4. PayPal 또는 카드로 결제

### 3.3 인스턴스 대여

#### 3.3.1 템플릿 선택
1. https://cloud.vast.ai/templates/ 접속
2. **PyTorch (Vast)** 클릭 (SSH, Jupyter 지원)

#### 3.3.2 GPU 인스턴스 선택

**권장 인스턴스:**
| 항목 | 권장값 |
|------|--------|
| GPU | RTX 3090 / RTX 3090 Ti |
| VRAM | 24GB |
| 가격 | $0.13-0.20/hr |
| Reliability | 99%+ |

**실제 사용 인스턴스 (2026-01-28):**
```
Type #19905787
Vietnam, VN
1x RTX 3090 Ti
24GB VRAM
$0.137/hr → $0.143/hr (50GB 디스크 포함)
Reliability: 99.48%
```

#### 3.3.3 디스크 크기 설정 (중요!)

⚠️ **Container Size를 반드시 50GB 이상으로 설정하세요!**

1. 인스턴스 선택 후 설정 화면에서
2. **Container Size**: `16.00` → `50` 으로 변경
3. **RENT** 클릭

> 기본값 16GB로는 8B 모델(~16GB) 다운로드 시 디스크 공간 부족 오류 발생

#### 3.3.4 대여 확정
1. **RENT** 버튼 클릭
2. 인스턴스 시작 대기 (1-2분)
3. **Instances** 탭에서 상태 확인: `running`

### 3.4 SSH 접속

#### 3.4.1 SSH 정보 확인
1. **Instances** 탭 접속
2. 실행 중인 인스턴스 행 클릭
3. **Connect** 버튼 클릭
4. **Direct ssh connect** 정보 확인

**예시:**
```
ssh -p 48122 root@27.64.192.151 -L 8080:localhost:8080
```

#### 3.4.2 SSH 접속 (로컬에서)
```bash
# 접속 정보 설정
export VAST_IP="27.64.192.151"  # 실제 IP로 변경
export VAST_PORT="48122"         # 실제 포트로 변경

# SSH 접속
ssh -i ~/.ssh/id_ed25519_vastai -p $VAST_PORT root@$VAST_IP -o StrictHostKeyChecking=no
```

#### 3.4.3 접속 확인
```bash
# GPU 확인
nvidia-smi --query-gpu=name,memory.total --format=csv
```

**예상 출력:**
```
name, memory.total [MiB]
NVIDIA GeForce RTX 3090 Ti, 24564 MiB
```

### 3.5 환경 설정 (인스턴스 내부)

⚠️ **중요: conda 환경 활성화 필수!**

```bash
# conda 환경 활성화 (필수!)
source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base

# 필수 패키지 설치
pip install torch transformers accelerate tqdm -q

# 작업 디렉토리 생성
mkdir -p /workspace/poc/data /workspace/poc/results
```

### 3.6 데이터 업로드 (로컬에서)

```bash
# 테스트 문항 업로드
scp -i ~/.ssh/id_ed25519_vastai -P $VAST_PORT -o StrictHostKeyChecking=no \
    /path/to/poc/data/test_items.json \
    root@$VAST_IP:/workspace/poc/data/
```

### 3.7 임베딩 생성 스크립트

#### 3.7.1 스크립트 생성 (인스턴스 내부)

```bash
cat > /workspace/poc/generate_8b_embeddings.py << 'SCRIPT_EOF'
#!/usr/bin/env python3
"""Qwen3-Embedding-8B 임베딩 생성"""
import torch
import json
from tqdm import tqdm

def main():
    MODEL_NAME = "Qwen/Qwen3-Embedding-8B"
    DATA_PATH = "/workspace/poc/data/test_items.json"
    OUTPUT_PATH = "/workspace/poc/results/qwen_embeddings_8b.json"

    print("=" * 60)
    print("Qwen3-Embedding-8B 임베딩 생성")
    print("=" * 60)

    print("\n[1/4] 모델 로드 중...")
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()

    print(f"모델 로드 완료! VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")

    print("\n[2/4] 데이터 로드 중...")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items", data) if isinstance(data, dict) else data
    print(f"문항 수: {len(items)}")

    print("\n[3/4] 임베딩 생성 중...")
    embeddings = {}
    instruction = "Represent this educational question item for retrieval."

    for item in tqdm(items, desc="Embedding"):
        item_id = item.get("id") or item.get("item_id")
        content = item.get("content", {})
        if isinstance(content, dict):
            question = content.get("question", "")
            choices = content.get("choices", [])
            text = f"문제: {question}"
            if choices:
                for i, c in enumerate(choices, 1):
                    text += f"\n{i}. {c}"
        else:
            text = str(content)

        if not text.strip():
            continue

        full_text = f"{instruction}\n{text}"
        inputs = tokenizer(full_text, return_tensors="pt", truncation=True, max_length=8192, padding=True).to(model.device)

        with torch.no_grad():
            outputs = model(**inputs)
            hidden_states = outputs.last_hidden_state
            attention_mask = inputs["attention_mask"]
            mask_expanded = attention_mask.unsqueeze(-1).expand(hidden_states.size()).float()
            sum_embeddings = torch.sum(hidden_states * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            embedding = (sum_embeddings / sum_mask).squeeze()
            embedding = torch.nn.functional.normalize(embedding, p=2, dim=-1)

        embeddings[item_id] = embedding.cpu().float().numpy().tolist()

    print("\n[4/4] 저장 중...")
    result = {
        "model": MODEL_NAME,
        "mode": "text_only",
        "num_items": len(embeddings),
        "embedding_dim": len(next(iter(embeddings.values()))) if embeddings else 0,
        "embeddings": embeddings
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"완료! {len(embeddings)}개 임베딩 생성")
    print(f"저장: {OUTPUT_PATH}")
    print(f"차원: {result['embedding_dim']}")
    print(f"최종 VRAM: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
    print("=" * 60)

if __name__ == "__main__":
    main()
SCRIPT_EOF
```

#### 3.7.2 스크립트 실행

```bash
source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base
cd /workspace/poc
python generate_8b_embeddings.py
```

#### 3.7.3 실제 출력 결과 (2026-01-28)

```
============================================================
Qwen3-Embedding-8B 임베딩 생성
============================================================

[1/4] 모델 로드 중...
모델 로드 완료! VRAM: 15.13 GB

[2/4] 데이터 로드 중...
문항 수: 100

[3/4] 임베딩 생성 중...
Embedding: 100%|██████████| 100/100 [02:15<00:00]

[4/4] 저장 중...

============================================================
완료! 100개 임베딩 생성
저장: /workspace/poc/results/qwen_embeddings_8b.json
차원: 4096
최종 VRAM: 15.17 GB
============================================================
```

### 3.8 결과 다운로드 (로컬에서)

```bash
scp -i ~/.ssh/id_ed25519_vastai -P $VAST_PORT -o StrictHostKeyChecking=no \
    root@$VAST_IP:/workspace/poc/results/qwen_embeddings_8b.json \
    /path/to/poc/results/
```

### 3.9 인스턴스 종료 (중요!)

⚠️ **종료하지 않으면 계속 과금됩니다!**

1. https://cloud.vast.ai/instances/ 접속
2. 인스턴스 행에서 **Destroy** 버튼 클릭
3. 확인 대화상자에서 **OK**

**확인:**
- Billing 탭에서 Current Usage가 모두 **$0.00**인지 확인

---

## 4. 문제 해결

### 4.1 디스크 공간 부족 오류

```
RuntimeError: No space left on device (os error 28)
```

**원인:** Container Size가 16GB(기본값)로 설정됨
**해결:** 인스턴스 삭제 후 Container Size 50GB 이상으로 재대여

### 4.2 python 명령어 없음

```
bash: python: command not found
```

**해결:** conda 환경 활성화 필수
```bash
source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base
```

### 4.3 torch 모듈 없음

```
ModuleNotFoundError: No module named 'torch'
```

**해결:** conda 환경에서 torch 설치
```bash
source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base
pip install torch transformers accelerate tqdm
```

### 4.4 SSH 접속 실패

```bash
# 권한 확인
chmod 600 ~/.ssh/id_ed25519_vastai

# verbose 모드로 디버깅
ssh -i ~/.ssh/id_ed25519_vastai -v -p <PORT> root@<IP>
```

---

## 5. 자동화 스크립트 (로컬에서 원격 실행)

전체 과정을 로컬에서 자동으로 실행:

```bash
#!/bin/bash
# run_8b_embedding.sh

VAST_IP="27.64.192.151"  # 실제 IP로 변경
VAST_PORT="48122"         # 실제 포트로 변경
SSH_KEY="~/.ssh/id_ed25519_vastai"
SSH_OPTS="-o StrictHostKeyChecking=no"

# 1. 환경 설정
ssh -i $SSH_KEY -p $VAST_PORT root@$VAST_IP $SSH_OPTS \
    "source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base && \
     pip install torch transformers accelerate tqdm -q && \
     mkdir -p /workspace/poc/data /workspace/poc/results"

# 2. 데이터 업로드
scp -i $SSH_KEY -P $VAST_PORT $SSH_OPTS \
    ./poc/data/test_items.json root@$VAST_IP:/workspace/poc/data/

# 3. 스크립트 업로드 및 실행
scp -i $SSH_KEY -P $VAST_PORT $SSH_OPTS \
    ./poc/scripts/generate_8b_embeddings.py root@$VAST_IP:/workspace/poc/

ssh -i $SSH_KEY -p $VAST_PORT root@$VAST_IP $SSH_OPTS \
    "source /opt/miniforge3/etc/profile.d/conda.sh && conda activate base && \
     cd /workspace/poc && python generate_8b_embeddings.py"

# 4. 결과 다운로드
scp -i $SSH_KEY -P $VAST_PORT $SSH_OPTS \
    root@$VAST_IP:/workspace/poc/results/qwen_embeddings_8b.json ./poc/results/

echo "완료! 인스턴스를 Destroy하세요."
```

---

## 6. 비용 요약 (실제)

| 항목 | 시간 | 비용 |
|------|------|------|
| 첫 번째 시도 (디스크 16GB, 실패) | ~10분 | ~$0.02 |
| 두 번째 시도 (디스크 50GB, 성공) | ~15분 | ~$0.04 |
| 디스크 과금 (종료 지연) | - | ~$0.52 |
| **총계** | **~25분** | **~$0.58** |

> 충전: $5.00 → 잔액: $4.42

---

## 7. 결과 파일

| 파일 | 위치 | 크기 |
|------|------|------|
| 8B 임베딩 | `poc/results/qwen_embeddings_8b.json` | 9.2MB |

**임베딩 사양:**
- 모델: Qwen/Qwen3-Embedding-8B
- 문항 수: 100
- 차원: 4096 (2B는 2048)
- 정규화: L2 normalized

---

## 문서 이력

| 버전 | 일자 | 변경 내용 |
|------|------|----------|
| v1.0.0 | 2026-01-28 | 최초 작성 |
| v1.0.1 | 2026-01-28 | SSH 키 파일명 변경 (id_ed25519_vastai), 공개키 업데이트 |
| v2.0.0 | 2026-01-28 | 실제 실행 결과 반영, 상세 절차 업데이트 |
| | | - Container Size 50GB 필수 강조 |
| | | - conda 환경 활성화 필수 추가 |
| | | - 실제 사용 스크립트로 업데이트 (Qwen3-Embedding-8B) |
| | | - 문제 해결 섹션 추가 |
| | | - 실제 비용 정보 추가 ($0.58) |
