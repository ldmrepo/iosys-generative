#!/usr/bin/env python3
"""
Vast.ai용 Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성 스크립트

사용법:
1. test_items.json 업로드
2. pip install torch transformers accelerate tqdm qwen-vl-utils Pillow
3. python vastai_qwen3vl_8b_embedding.py

출력: qwen_vl_embeddings_8b.json
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
BATCH_SIZE = 1  # 8B 모델은 메모리 이슈로 batch=1 권장
MAX_LENGTH = 4096


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        return f"Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB"
    return "N/A"


def load_model():
    """Qwen3-VL-Embedding-8B 모델 로드"""
    from transformers import AutoModel, AutoTokenizer, AutoProcessor

    print(f"Loading model: {MODEL_NAME}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    # Processor and Tokenizer
    processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)

    # Model with bfloat16
    model = AutoModel.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()

    print(f"Model loaded. GPU memory: {get_gpu_memory()}")
    return model, processor


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


def format_message(text, image_path=None):
    """Qwen3-VL 메시지 포맷"""
    instruction = "Represent this educational question item for retrieval."

    content = []

    # 이미지가 있으면 추가
    if image_path and Path(image_path).exists():
        content.append({
            "type": "image",
            "image": f"file://{image_path}"
        })

    # 텍스트 추가
    content.append({
        "type": "text",
        "text": text
    })

    messages = [
        {"role": "system", "content": [{"type": "text", "text": instruction}]},
        {"role": "user", "content": content}
    ]

    return messages


@torch.no_grad()
def generate_embedding(model, processor, text, image_path=None):
    """단일 문항 임베딩 생성 (mean pooling)"""
    from qwen_vl_utils import process_vision_info

    messages = format_message(text, image_path)

    # Apply chat template
    text_input = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    # Process vision info
    try:
        image_inputs, video_inputs = process_vision_info(messages)
    except Exception:
        image_inputs = None
        video_inputs = None

    # Tokenize
    inputs = processor(
        text=[text_input],
        images=image_inputs,
        videos=video_inputs,
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
    print("Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성")
    print("=" * 70)

    # 1. 데이터 로드
    print(f"\n[1/3] 데이터 로드: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data['items']
    print(f"      문항 수: {len(items)}")

    # 이미지 문항 확인
    image_items = [item for item in items if item.get('has_image')]
    print(f"      이미지 문항: {len(image_items)}")
    print(f"      텍스트 문항: {len(items) - len(image_items)}")

    # 2. 모델 로드
    print("\n[2/3] 모델 로드...")
    model, processor = load_model()

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

            # 이미지 경로 (Vast.ai에서는 이미지 없음)
            image_path = None

            embedding = generate_embedding(model, processor, text, image_path)
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
            "mode": "multimodal_meanpool",
            "note": "Text-only (no images on Vast.ai)",
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
