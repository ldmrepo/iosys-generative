#!/usr/bin/env python3
"""
Vast.ai용 Qwen3-VL-Embedding-8B 전체 임베딩 생성 (10,952건)
- 체크포인트 지원 (중단 후 재개 가능)
- 텍스트 전용 (Vast.ai에 이미지 없음)
"""

import json
import torch
import torch.nn.functional as F
import gc
import time
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Configuration
MODEL_NAME = "Qwen/Qwen3-VL-Embedding-8B"
DATA_FILE = "items_full.json"
OUTPUT_FILE = "qwen_vl_embeddings_full_8b.json"
CHECKPOINT_FILE = "checkpoint_8b.json"
MAX_LENGTH = 4096
SAVE_INTERVAL = 500  # 500개마다 체크포인트 저장


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"


def load_model():
    """Qwen3-VL-Embedding-8B 모델 로드"""
    from transformers import AutoModel, AutoTokenizer

    print(f"Loading model: {MODEL_NAME}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

    model = AutoModel.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()

    print(f"Model loaded. GPU memory: {get_gpu_memory()}")
    return model, tokenizer


def prepare_text(item):
    """문항 텍스트 준비"""
    content = item.get('content', {})
    question = content.get('question', '')
    choices = content.get('choices', [])

    text = f"문제: {question}"
    if choices:
        choices_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(choices)])
        text += f"\n선택지:\n{choices_text}"

    return text


@torch.no_grad()
def generate_embedding(model, tokenizer, text):
    """단일 문항 임베딩 생성 (mean pooling)"""
    instruction = "Instruct: Represent this educational question item for retrieval.\nQuery: "
    full_text = instruction + text

    inputs = tokenizer(
        full_text,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt"
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    outputs = model(**inputs)

    attention_mask = inputs['attention_mask']
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    embeddings = F.normalize(embeddings, p=2, dim=-1)

    return embeddings[0].cpu().float().numpy().tolist()


def load_checkpoint():
    """체크포인트 로드"""
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"embeddings": {}, "completed_ids": set(), "errors": []}


def save_checkpoint(embeddings, completed_ids, errors):
    """체크포인트 저장"""
    checkpoint = {
        "embeddings": embeddings,
        "completed_ids": list(completed_ids),
        "errors": errors,
        "saved_at": datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f)


def main():
    start_time = time.time()

    print("=" * 70)
    print("Qwen3-VL-Embedding-8B 전체 임베딩 생성")
    print("=" * 70)

    # 1. 데이터 로드
    print(f"\n[1/4] 데이터 로드: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data['items']
    print(f"      총 문항: {len(items):,}개")

    # 2. 체크포인트 로드
    print("\n[2/4] 체크포인트 확인...")
    checkpoint = load_checkpoint()
    embeddings = checkpoint.get("embeddings", {})
    completed_ids = set(checkpoint.get("completed_ids", []))
    errors = checkpoint.get("errors", [])

    remaining_items = [item for item in items if item['id'] not in completed_ids]
    print(f"      기존 완료: {len(completed_ids):,}개")
    print(f"      남은 문항: {len(remaining_items):,}개")

    if len(remaining_items) == 0:
        print("      이미 모든 문항 완료!")
        return

    # 3. 모델 로드
    print("\n[3/4] 모델 로드...")
    model, tokenizer = load_model()
    hidden_size = model.config.text_config.hidden_size
    print(f"      임베딩 차원: {hidden_size}")

    # 4. 임베딩 생성
    print("\n[4/4] 임베딩 생성...")

    for i, item in enumerate(tqdm(remaining_items, desc="Generating embeddings")):
        item_id = item['id']

        try:
            text = prepare_text(item)
            embedding = generate_embedding(model, tokenizer, text)
            embeddings[item_id] = embedding
            completed_ids.add(item_id)

        except Exception as e:
            errors.append({"id": item_id, "error": str(e)})
            print(f"\nError for {item_id}: {e}")

        # 체크포인트 저장
        if (i + 1) % SAVE_INTERVAL == 0:
            save_checkpoint(embeddings, completed_ids, errors)
            elapsed = time.time() - start_time
            speed = len(completed_ids) / elapsed if elapsed > 0 else 0
            remaining = len(items) - len(completed_ids)
            eta = remaining / speed / 60 if speed > 0 else 0
            print(f"\n      체크포인트 저장: {len(completed_ids):,}/{len(items):,} ({speed:.1f}/sec, ETA: {eta:.1f}min)")

    # 5. 최종 저장
    print("\n최종 결과 저장 중...")

    elapsed = time.time() - start_time

    output = {
        "model": MODEL_NAME,
        "mode": "text_only_meanpool",
        "num_items": len(embeddings),
        "embedding_dim": hidden_size,
        "metadata": {
            "total": len(items),
            "completed": len(embeddings),
            "errors": len(errors),
            "elapsed_seconds": elapsed,
            "items_per_second": len(embeddings) / elapsed if elapsed > 0 else 0
        },
        "embeddings": embeddings,
        "errors": errors
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f)

    # 체크포인트 삭제
    if Path(CHECKPOINT_FILE).exists():
        Path(CHECKPOINT_FILE).unlink()

    print(f"\n저장 완료: {OUTPUT_FILE}")
    print(f"파일 크기: {Path(OUTPUT_FILE).stat().st_size / 1024 / 1024:.1f} MB")
    print(f"최종 GPU 메모리: {get_gpu_memory()}")

    # Cleanup
    del model
    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 70)
    print(f"완료! {len(embeddings):,}개 임베딩 생성")
    print(f"에러: {len(errors)}개")
    print(f"소요 시간: {elapsed/60:.1f}분")
    print(f"처리 속도: {len(embeddings)/elapsed:.2f} items/sec")
    print("=" * 70)


if __name__ == "__main__":
    main()
