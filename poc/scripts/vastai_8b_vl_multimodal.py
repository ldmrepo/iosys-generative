#!/usr/bin/env python3
"""
Vast.ai용 Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성
- 텍스트 + 이미지 처리
- 체크포인트 지원
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
IMAGE_DIR = Path("./images")  # 압축 해제된 이미지 폴더
OUTPUT_FILE = "qwen_vl_embeddings_full_8b_multimodal.json"
CHECKPOINT_FILE = "checkpoint_8b_mm.json"
MAX_LENGTH = 4096
SAVE_INTERVAL = 500


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"


def find_image_path(item_id):
    """문항 ID에 해당하는 이미지 경로 찾기"""
    if not IMAGE_DIR.exists():
        return None

    def check_item_dir(item_path):
        """item_path에서 이미지 찾기"""
        if not item_path.exists():
            return None
        # DrawObjPic 폴더 내 이미지
        draw_path = item_path / "DrawObjPic"
        if draw_path.exists():
            for img_file in draw_path.glob("*.png"):
                return str(img_file)
            for img_file in draw_path.glob("*.jpg"):
                return str(img_file)
        # 직접 이미지
        for img_file in item_path.glob("*.png"):
            return str(img_file)
        for img_file in item_path.glob("*.jpg"):
            return str(img_file)
        return None

    # 패턴 1: YYYYMMDD/item_id/ (구형)
    for date_dir in IMAGE_DIR.iterdir():
        if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
            result = check_item_dir(date_dir / item_id)
            if result:
                return result

    # 패턴 2: YYYY/MM/DD/item_id/ (신형)
    for year_dir in IMAGE_DIR.iterdir():
        if year_dir.is_dir() and year_dir.name.isdigit() and len(year_dir.name) == 4:
            for month_dir in year_dir.iterdir():
                if month_dir.is_dir():
                    for day_dir in month_dir.iterdir():
                        if day_dir.is_dir():
                            result = check_item_dir(day_dir / item_id)
                            if result:
                                return result

    return None


def load_model():
    """Qwen3-VL-Embedding-8B 모델 로드 (멀티모달)"""
    from transformers import AutoModel, AutoProcessor

    print(f"Loading model: {MODEL_NAME}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    model = AutoModel.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()

    processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)

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


@torch.no_grad()
def generate_embedding(model, processor, text, image_path=None):
    """멀티모달 임베딩 생성 (mean pooling)"""
    from qwen_vl_utils import process_vision_info

    instruction = "Represent this educational question item for retrieval."

    # 메시지 구성
    content = []
    if image_path and Path(image_path).exists():
        content.append({
            "type": "image",
            "image": f"file://{image_path}",
            "min_pixels": 4 * 32 * 32,
            "max_pixels": 1280 * 32 * 32
        })
    content.append({"type": "text", "text": text})

    messages = [
        {"role": "system", "content": [{"type": "text", "text": instruction}]},
        {"role": "user", "content": content}
    ]

    # 텍스트 처리
    text_input = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    # 이미지 처리
    try:
        image_inputs, video_inputs = process_vision_info(messages)
    except Exception:
        image_inputs = None
        video_inputs = None

    # 입력 준비
    inputs = processor(
        text=[text_input],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt"
    ).to(model.device)

    # Forward pass
    outputs = model(**inputs)
    last_hidden_state = outputs.last_hidden_state

    # Mean pooling
    attention_mask = inputs["attention_mask"]
    mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    sum_embeddings = torch.sum(last_hidden_state * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    embedding = sum_embeddings / sum_mask

    # Normalize
    embedding = F.normalize(embedding, p=2, dim=-1)

    return embedding[0].cpu().float().numpy().tolist()


@torch.no_grad()
def generate_embedding_text_only(model, processor, text):
    """텍스트 전용 임베딩 (이미지 없을 때)"""
    instruction = "Represent this educational question item for retrieval."

    messages = [
        {"role": "system", "content": [{"type": "text", "text": instruction}]},
        {"role": "user", "content": [{"type": "text", "text": text}]}
    ]

    text_input = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = processor(
        text=[text_input],
        padding=True,
        return_tensors="pt"
    ).to(model.device)

    outputs = model(**inputs)
    last_hidden_state = outputs.last_hidden_state

    attention_mask = inputs["attention_mask"]
    mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    sum_embeddings = torch.sum(last_hidden_state * mask_expanded, dim=1)
    sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
    embedding = sum_embeddings / sum_mask

    embedding = F.normalize(embedding, p=2, dim=-1)

    return embedding[0].cpu().float().numpy().tolist()


def load_checkpoint():
    """체크포인트 로드"""
    if Path(CHECKPOINT_FILE).exists():
        with open(CHECKPOINT_FILE, 'r') as f:
            return json.load(f)
    return {"embeddings": {}, "completed_ids": [], "errors": [], "image_count": 0}


def save_checkpoint(embeddings, completed_ids, errors, image_count):
    """체크포인트 저장"""
    checkpoint = {
        "embeddings": embeddings,
        "completed_ids": list(completed_ids),
        "errors": errors,
        "image_count": image_count,
        "saved_at": datetime.now().isoformat()
    }
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f)


def main():
    start_time = time.time()

    print("=" * 70)
    print("Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성")
    print("=" * 70)

    # 1. 데이터 로드
    print(f"\n[1/5] 데이터 로드: {DATA_FILE}")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data['items']
    print(f"      총 문항: {len(items):,}개")

    # 2. 이미지 디렉토리 확인
    print(f"\n[2/5] 이미지 디렉토리 확인: {IMAGE_DIR}")
    if IMAGE_DIR.exists():
        img_count = sum(1 for _ in IMAGE_DIR.rglob("*.png")) + sum(1 for _ in IMAGE_DIR.rglob("*.jpg"))
        print(f"      이미지 파일: {img_count:,}개")
    else:
        print(f"      ⚠️  이미지 디렉토리 없음 - 텍스트 전용 모드")

    # 3. 체크포인트 로드
    print("\n[3/5] 체크포인트 확인...")
    checkpoint = load_checkpoint()
    embeddings = checkpoint.get("embeddings", {})
    completed_ids = set(checkpoint.get("completed_ids", []))
    errors = checkpoint.get("errors", [])
    image_count = checkpoint.get("image_count", 0)

    remaining_items = [item for item in items if item['id'] not in completed_ids]
    print(f"      기존 완료: {len(completed_ids):,}개")
    print(f"      남은 문항: {len(remaining_items):,}개")

    if len(remaining_items) == 0:
        print("      이미 모든 문항 완료!")
        return

    # 4. 모델 로드
    print("\n[4/5] 모델 로드...")
    model, processor = load_model()

    # hidden_size 확인
    if hasattr(model.config, 'hidden_size'):
        hidden_size = model.config.hidden_size
    elif hasattr(model.config, 'text_config'):
        hidden_size = model.config.text_config.hidden_size
    else:
        hidden_size = 4096  # default for 8B
    print(f"      임베딩 차원: {hidden_size}")

    # 5. 임베딩 생성
    print("\n[5/5] 임베딩 생성...")

    for i, item in enumerate(tqdm(remaining_items, desc="Generating embeddings")):
        item_id = item['id']

        try:
            text = prepare_text(item)
            image_path = find_image_path(item_id) if item.get("has_image", False) else None

            if image_path:
                embedding = generate_embedding(model, processor, text, image_path)
                image_count += 1
            else:
                embedding = generate_embedding_text_only(model, processor, text)

            embeddings[item_id] = embedding
            completed_ids.add(item_id)

        except Exception as e:
            errors.append({"id": item_id, "error": str(e)[:200]})
            print(f"\nError for {item_id}: {str(e)[:100]}")

        # 체크포인트 저장
        if (i + 1) % SAVE_INTERVAL == 0:
            save_checkpoint(embeddings, completed_ids, errors, image_count)
            elapsed = time.time() - start_time
            speed = len(completed_ids) / elapsed if elapsed > 0 else 0
            remaining = len(items) - len(completed_ids)
            eta = remaining / speed / 60 if speed > 0 else 0
            print(f"\n      체크포인트: {len(completed_ids):,}/{len(items):,} (이미지: {image_count}, {speed:.1f}/sec, ETA: {eta:.1f}min)")

        # 메모리 정리
        if (i + 1) % 100 == 0:
            gc.collect()
            torch.cuda.empty_cache()

    # 최종 저장
    print("\n최종 결과 저장 중...")

    elapsed = time.time() - start_time

    output = {
        "model": MODEL_NAME,
        "mode": "multimodal_meanpool",
        "num_items": len(embeddings),
        "embedding_dim": hidden_size,
        "metadata": {
            "total": len(items),
            "completed": len(embeddings),
            "with_image": image_count,
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

    # Cleanup
    del model
    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 70)
    print(f"완료! {len(embeddings):,}개 임베딩 생성")
    print(f"이미지 포함: {image_count:,}개")
    print(f"에러: {len(errors)}개")
    print(f"소요 시간: {elapsed/60:.1f}분")
    print(f"처리 속도: {len(embeddings)/elapsed:.2f} items/sec")
    print("=" * 70)


if __name__ == "__main__":
    main()
