#!/usr/bin/env python3
"""
Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성
- 18개 파트 파일 로드 지원 (176,443개 문항)
- 텍스트 + 이미지 처리
- 체크포인트 지원
- 로컬/Vast.ai 경로 자동 감지
- NumPy (.npz) 형식으로 저장 (JSON 대비 ~5배 압축)
"""

import json
import numpy as np
import torch
import torch.nn.functional as F
import gc
import time
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Configuration
MODEL_NAME = "Qwen/Qwen3-VL-Embedding-8B"
OUTPUT_FILE = "qwen_vl_embeddings_full_8b_multimodal.npz"
CHECKPOINT_FILE = "checkpoint_8b_mm.npz"
CHECKPOINT_META_FILE = "checkpoint_8b_mm_meta.json"
MAX_LENGTH = 4096
SAVE_INTERVAL = 500


def get_paths():
    """환경에 맞는 경로 반환"""
    # 로컬 환경
    local_base = Path("/root/work/mcp/iosys-generative")
    if local_base.exists():
        return {
            "image_dir": local_base / "data/raw",
            "items_dir": local_base / "data/processed",
            "output_dir": local_base / "poc/results"
        }

    # Vast.ai 환경 (홈 디렉토리 기준)
    home = Path.home()
    return {
        "image_dir": home / "data/raw",
        "items_dir": home / "data/processed",
        "output_dir": home / "poc/results"
    }


def load_all_items(items_dir):
    """18개 파트 파일에서 모든 문항 로드"""
    all_items = []
    for i in range(1, 19):
        file_path = items_dir / f"items_part{i:02d}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("items", data)
                all_items.extend(items)
                print(f"  Part {i:02d}: {len(items):,} items")
        else:
            print(f"  Part {i:02d}: 파일 없음")
    return all_items


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"


def find_image_path(item_id, image_dir):
    """문항 ID에 해당하는 이미지 경로 찾기"""
    if not image_dir.exists():
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
    for date_dir in image_dir.iterdir():
        if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
            result = check_item_dir(date_dir / item_id)
            if result:
                return result

    # 패턴 2: YYYY/MM/DD/item_id/ (신형)
    for year_dir in image_dir.iterdir():
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

    return embedding[0].cpu().float().numpy()


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

    return embedding[0].cpu().float().numpy()


def load_checkpoint(output_dir):
    """체크포인트 로드 (NumPy + JSON 메타데이터)"""
    checkpoint_file = output_dir / CHECKPOINT_FILE
    meta_file = output_dir / CHECKPOINT_META_FILE

    if checkpoint_file.exists() and meta_file.exists():
        # 메타데이터 로드
        with open(meta_file, 'r') as f:
            meta = json.load(f)

        # 임베딩 로드
        data = np.load(checkpoint_file, allow_pickle=True)
        item_ids = data['item_ids'].tolist()
        embeddings_array = data['embeddings']

        # dict로 변환
        embeddings = {item_id: embeddings_array[i] for i, item_id in enumerate(item_ids)}

        return {
            "embeddings": embeddings,
            "completed_ids": meta.get("completed_ids", []),
            "errors": meta.get("errors", []),
            "image_count": meta.get("image_count", 0)
        }

    return {"embeddings": {}, "completed_ids": [], "errors": [], "image_count": 0}


def save_checkpoint(output_dir, embeddings, completed_ids, errors, image_count):
    """체크포인트 저장 (NumPy + JSON 메타데이터)"""
    checkpoint_file = output_dir / CHECKPOINT_FILE
    meta_file = output_dir / CHECKPOINT_META_FILE

    # 임베딩을 numpy 배열로 변환
    item_ids = list(embeddings.keys())
    if item_ids:
        embeddings_array = np.array([embeddings[item_id] for item_id in item_ids], dtype=np.float32)
        np.savez_compressed(checkpoint_file, item_ids=np.array(item_ids), embeddings=embeddings_array)

    # 메타데이터 저장 (JSON)
    meta = {
        "completed_ids": list(completed_ids),
        "errors": errors,
        "image_count": image_count,
        "saved_at": datetime.now().isoformat()
    }
    with open(meta_file, 'w') as f:
        json.dump(meta, f)


def main():
    start_time = time.time()

    print("=" * 70)
    print("Qwen3-VL-Embedding-8B 멀티모달 임베딩 생성 (176,443 items)")
    print("=" * 70)

    # 경로 설정
    paths = get_paths()
    image_dir = paths["image_dir"]
    items_dir = paths["items_dir"]
    output_dir = paths["output_dir"]

    print(f"\n이미지 디렉토리: {image_dir}")
    print(f"문항 디렉토리: {items_dir}")
    print(f"출력 디렉토리: {output_dir}")

    # 출력 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / OUTPUT_FILE

    # 1. 데이터 로드
    print(f"\n[1/5] 데이터 로드...")
    items = load_all_items(items_dir)
    print(f"      총 문항: {len(items):,}개")

    if len(items) == 0:
        print("❌ 문항을 찾을 수 없습니다.")
        return

    # 2. 이미지 디렉토리 확인
    print(f"\n[2/5] 이미지 디렉토리 확인: {image_dir}")
    if image_dir.exists():
        img_count = sum(1 for _ in image_dir.rglob("*.png")) + sum(1 for _ in image_dir.rglob("*.jpg"))
        print(f"      이미지 파일: {img_count:,}개")
    else:
        print(f"      ⚠️  이미지 디렉토리 없음 - 텍스트 전용 모드")

    # 3. 체크포인트 로드
    print("\n[3/5] 체크포인트 확인...")
    checkpoint = load_checkpoint(output_dir)
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
            image_path = find_image_path(item_id, image_dir) if item.get("has_image", False) else None

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
            save_checkpoint(output_dir, embeddings, completed_ids, errors, image_count)
            elapsed = time.time() - start_time
            speed = len(completed_ids) / elapsed if elapsed > 0 else 0
            remaining = len(items) - len(completed_ids)
            eta = remaining / speed / 60 if speed > 0 else 0
            print(f"\n      체크포인트: {len(completed_ids):,}/{len(items):,} (이미지: {image_count}, {speed:.1f}/sec, ETA: {eta:.1f}min)")

        # 메모리 정리
        if (i + 1) % 100 == 0:
            gc.collect()
            torch.cuda.empty_cache()

    # 최종 저장 (NumPy .npz 형식)
    print("\n최종 결과 저장 중 (NumPy .npz 형식)...")

    elapsed = time.time() - start_time

    # 임베딩을 numpy 배열로 변환
    item_ids = list(embeddings.keys())
    embeddings_array = np.array([embeddings[item_id] for item_id in item_ids], dtype=np.float32)

    # 메타데이터
    metadata = {
        "model": MODEL_NAME,
        "mode": "multimodal_meanpool",
        "num_items": len(embeddings),
        "embedding_dim": hidden_size,
        "total": len(items),
        "completed": len(embeddings),
        "with_image": image_count,
        "errors_count": len(errors),
        "elapsed_seconds": elapsed,
        "items_per_second": len(embeddings) / elapsed if elapsed > 0 else 0
    }

    # NumPy 압축 저장
    np.savez_compressed(
        output_file,
        item_ids=np.array(item_ids),
        embeddings=embeddings_array,
        metadata=np.array([json.dumps(metadata)]),  # 메타데이터는 JSON 문자열로
        errors=np.array([json.dumps(errors)])  # 에러도 JSON 문자열로
    )

    # 체크포인트 삭제
    checkpoint_file = output_dir / CHECKPOINT_FILE
    meta_file = output_dir / CHECKPOINT_META_FILE
    if checkpoint_file.exists():
        checkpoint_file.unlink()
    if meta_file.exists():
        meta_file.unlink()

    print(f"\n저장 완료: {output_file}")
    print(f"파일 크기: {output_file.stat().st_size / 1024 / 1024:.1f} MB")

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
