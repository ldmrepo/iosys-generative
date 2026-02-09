#!/usr/bin/env python3
"""
Vast.ai용 Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성 스크립트 v2
- AutoProcessor 대신 Qwen3VLProcessor 직접 사용
"""

import json
import torch
import torch.nn.functional as F
import gc
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Configuration
MODEL_NAME = "Qwen/Qwen3-VL-Embedding-8B"
DATA_FILE = "test_items.json"
OUTPUT_FILE = "qwen_vl_embeddings_8b.json"
MAX_LENGTH = 4096


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        return f"Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB"
    return "N/A"


def load_model():
    """Qwen3-VL-Embedding-8B 모델 로드"""
    from transformers import AutoModel, AutoTokenizer

    print(f"Loading model: {MODEL_NAME}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)

    # Model with bfloat16
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
    # Instruction prefix
    instruction = "Instruct: Represent this educational question item for retrieval.\nQuery: "
    full_text = instruction + text

    # Tokenize
    inputs = tokenizer(
        full_text,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt"
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    # Forward pass
    outputs = model(**inputs)

    # Mean pooling
    attention_mask = inputs['attention_mask']
    token_embeddings = outputs.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    # L2 normalize
    embeddings = F.normalize(embeddings, p=2, dim=-1)

    return embeddings[0].cpu().float().numpy().tolist()


def main():
    print("=" * 70)
    print("Qwen3-VL-Embedding-8B 임베딩 생성 (텍스트 전용)")
    print("=" * 70)

    # 1. 데이터 로드
    print(f"\n[1/3] 데이터 로드: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data['items']
    print(f"      문항 수: {len(items)}")

    # 2. 모델 로드
    print("\n[2/3] 모델 로드...")
    model, tokenizer = load_model()

    # 임베딩 차원 확인
    hidden_size = model.config.hidden_size
    print(f"      임베딩 차원: {hidden_size}")

    # 3. 임베딩 생성
    print("\n[3/3] 임베딩 생성...")
    embeddings = {}
    errors = []

    for item in tqdm(items, desc="Generating embeddings"):
        item_id = item['id']

        try:
            text = prepare_text(item)
            embedding = generate_embedding(model, tokenizer, text)
            embeddings[item_id] = embedding

        except Exception as e:
            errors.append({"id": item_id, "error": str(e)})
            print(f"\nError for {item_id}: {e}")

    # 4. 저장
    print(f"\n성공: {len(embeddings)}/{len(items)}")
    if errors:
        print(f"오류: {len(errors)}")

    output = {
        "metadata": {
            "model": MODEL_NAME,
            "mode": "text_only_meanpool",
            "note": "Qwen3-VL-Embedding-8B with text-only input and mean pooling",
            "total_items": len(items),
            "successful": len(embeddings),
            "failed": len(errors),
            "embedding_dim": hidden_size,
            "dtype": "bfloat16",
            "created_at": datetime.now().isoformat()
        },
        "embeddings": embeddings,
        "errors": errors
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"\n저장 완료: {OUTPUT_FILE}")
    print(f"파일 크기: {Path(OUTPUT_FILE).stat().st_size / 1024 / 1024:.1f} MB")
    print(f"최종 GPU 메모리: {get_gpu_memory()}")

    # Cleanup
    del model
    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
