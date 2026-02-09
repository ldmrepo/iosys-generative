#!/usr/bin/env python3
"""
Qwen3-VL-Embedding-8B 샘플 테스트 (1000개)
- Qwen3VLEmbedder 클래스 사용 (공식 권장 방식)
- 100개 테스트 아이템 포함하여 평가 가능하도록 샘플링
"""

import json
import numpy as np
import torch
import random
import gc
import time
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Configuration
MODEL_NAME = "Qwen/Qwen3-VL-Embedding-8B"
OUTPUT_FILE = "qwen_vl_embeddings_8b_sample_1000.json"
SAMPLE_SIZE = 1000
SEED = 42


def get_paths():
    """환경에 맞는 경로 반환"""
    local_base = Path("/root/work/mcp/iosys-generative")
    if local_base.exists():
        return {
            "image_dir": local_base / "data/raw",
            "items_dir": local_base / "data/processed",
            "output_dir": local_base / "poc/results",
            "test_items": local_base / "poc/data/test_items.json"
        }

    home = Path.home()
    return {
        "image_dir": home / "data/raw",
        "items_dir": home / "data/processed",
        "output_dir": home / "poc/results",
        "test_items": home / "poc/data/test_items.json"
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
    return all_items


def load_test_items(test_items_path):
    """테스트 아이템 ID 로드"""
    if not test_items_path.exists():
        return set()
    with open(test_items_path) as f:
        data = json.load(f)
    return set(item["id"] for item in data["items"])


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
        if not item_path.exists():
            return None
        draw_path = item_path / "DrawObjPic"
        if draw_path.exists():
            for img_file in draw_path.glob("*.png"):
                return str(img_file)
            for img_file in draw_path.glob("*.jpg"):
                return str(img_file)
        for img_file in item_path.glob("*.png"):
            return str(img_file)
        for img_file in item_path.glob("*.jpg"):
            return str(img_file)
        return None

    # 패턴 1: YYYYMMDD/item_id/
    for date_dir in image_dir.iterdir():
        if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
            result = check_item_dir(date_dir / item_id)
            if result:
                return result

    # 패턴 2: YYYY/MM/DD/item_id/
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


def main():
    print("="*70)
    print("  Qwen3-VL-Embedding-8B 샘플 테스트 (Qwen3VLEmbedder 사용)")
    print("="*70)

    paths = get_paths()
    print(f"\n경로 설정:")
    for k, v in paths.items():
        exists = "✓" if v.exists() else "✗"
        print(f"  {k}: {v} [{exists}]")

    # 전체 문항 로드
    print(f"\n문항 로드 중...")
    all_items = load_all_items(paths["items_dir"])
    print(f"  전체 문항 수: {len(all_items):,}")

    # 테스트 아이템 로드
    test_item_ids = load_test_items(paths["test_items"])
    print(f"  테스트 아이템 수: {len(test_item_ids)}")

    # 샘플링: 테스트 아이템 100개 + 랜덤 900개
    random.seed(SEED)

    test_items = [item for item in all_items if item["id"] in test_item_ids]
    other_items = [item for item in all_items if item["id"] not in test_item_ids]

    # 이미지 포함 아이템 우선 샘플링
    other_with_image = [item for item in other_items if item.get("has_image")]
    other_no_image = [item for item in other_items if not item.get("has_image")]

    # 900개 중 300개는 이미지 포함
    sample_with_image = random.sample(other_with_image, min(300, len(other_with_image)))
    sample_no_image = random.sample(other_no_image, min(600, len(other_no_image)))

    sample_items = test_items + sample_with_image + sample_no_image
    random.shuffle(sample_items)

    print(f"\n샘플링 결과:")
    print(f"  - 테스트 아이템: {len(test_items)}")
    print(f"  - 추가 이미지 포함: {len(sample_with_image)}")
    print(f"  - 추가 이미지 없음: {len(sample_no_image)}")
    print(f"  - 총 샘플: {len(sample_items)}")

    # 모델 로드 (Qwen3VLEmbedder 사용)
    print(f"\n모델 로드 중: {MODEL_NAME}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    # Qwen3VLEmbedder 임포트 (scripts 폴더에서)
    import sys
    # HuggingFace 모델의 scripts 폴더 추가
    from huggingface_hub import snapshot_download
    model_path = snapshot_download(MODEL_NAME)
    sys.path.insert(0, str(Path(model_path) / "scripts"))

    from qwen3_vl_embedding import Qwen3VLEmbedder

    model = Qwen3VLEmbedder(
        model_name_or_path=MODEL_NAME,
        torch_dtype=torch.bfloat16
    )
    print(f"Model loaded. GPU memory: {get_gpu_memory()}")

    # 임베딩 생성
    print(f"\n임베딩 생성 시작...")
    start_time = time.time()

    embeddings = {}
    errors = []
    image_count = 0

    for item in tqdm(sample_items, desc="Generating embeddings"):
        item_id = item["id"]
        text = prepare_text(item)

        # 이미지 찾기
        image_path = None
        if item.get("has_image"):
            image_path = find_image_path(item_id, paths["image_dir"])

        try:
            # Qwen3VLEmbedder 입력 형식
            inputs = [{"text": text}]
            if image_path:
                inputs = [{"text": text, "image": image_path}]
                image_count += 1

            # 임베딩 생성
            emb = model.process(inputs)
            embeddings[item_id] = emb[0].tolist()

        except Exception as e:
            errors.append({"item_id": item_id, "error": str(e)})
            # 텍스트만으로 재시도
            try:
                inputs = [{"text": text}]
                emb = model.process(inputs)
                embeddings[item_id] = emb[0].tolist()
            except Exception as e2:
                errors.append({"item_id": item_id, "error": f"Retry failed: {str(e2)}"})

        # 메모리 정리 (100개마다)
        if len(embeddings) % 100 == 0:
            gc.collect()
            torch.cuda.empty_cache()

    elapsed = time.time() - start_time

    # 결과 저장
    output = {
        "metadata": {
            "model": MODEL_NAME,
            "method": "Qwen3VLEmbedder (official)",
            "embedding_dim": len(list(embeddings.values())[0]) if embeddings else 0,
            "total_items": len(sample_items),
            "successful": len(embeddings),
            "with_image": image_count,
            "errors": len(errors),
            "elapsed_seconds": elapsed,
            "items_per_second": len(embeddings) / elapsed if elapsed > 0 else 0,
            "created_at": datetime.now().isoformat()
        },
        "embeddings": embeddings,
        "errors": errors
    }

    output_path = paths["output_dir"] / OUTPUT_FILE
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)

    print(f"\n" + "="*70)
    print(f"  완료!")
    print(f"="*70)
    print(f"  총 임베딩: {len(embeddings):,}")
    print(f"  이미지 포함: {image_count}")
    print(f"  에러: {len(errors)}")
    print(f"  소요 시간: {elapsed/60:.1f}분")
    print(f"  처리 속도: {len(embeddings)/elapsed:.2f} items/sec")
    print(f"  출력 파일: {output_path}")
    print(f"="*70)


if __name__ == "__main__":
    main()
