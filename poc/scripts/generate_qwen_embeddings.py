#!/usr/bin/env python3
"""
Task #7 & #8: Qwen3-VL-Embedding-2B 임베딩 생성
텍스트 + 이미지 멀티모달 임베딩 생성

Uses the official Qwen3VLEmbedder wrapper for proper multimodal processing.
"""
import json
import sys
import torch
import gc
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-embedding-2b"
DATA_DIR = POC_DIR / "data"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")
OUTPUT_DIR = POC_DIR / "results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Add model scripts to path for Qwen3VLEmbedder
sys.path.insert(0, str(MODEL_PATH / "scripts"))

def get_gpu_memory():
    """GPU 메모리 사용량"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"

def load_model():
    """모델 로드 - Qwen3VLEmbedder 래퍼 사용"""
    from qwen3_vl_embedding import Qwen3VLEmbedder

    print(f"Loading model from {MODEL_PATH}...")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    model = Qwen3VLEmbedder(
        model_name_or_path=str(MODEL_PATH),
        torch_dtype=torch.float16,
        default_instruction="Represent this educational question item for retrieval."
    )

    print(f"Model loaded. GPU memory: {get_gpu_memory()}")

    return model

def load_test_items():
    """테스트 데이터 로드"""
    with open(DATA_DIR / "test_items.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['items']

def prepare_text_input(item):
    """문항에서 텍스트 입력 준비"""
    content = item.get('content', {})

    # 문제 텍스트
    question = content.get('question', '')

    # 선택지 (있으면)
    choices = content.get('choices', [])
    choices_text = ""
    if choices:
        for i, choice in enumerate(choices, 1):
            choices_text += f"\n{i}. {choice}"

    # 전체 텍스트
    text = f"문제: {question}"
    if choices_text:
        text += f"\n선택지:{choices_text}"

    return text

def find_image_path(item):
    """문항의 이미지 경로 찾기 (question + explanation)

    두 가지 폴더 구조 지원:
    1. YYYYMMDD: {RAW_IMAGE_DIR}/20150226/{item_id}/DrawObjPic/{filename}
    2. YYYY/MM/DD: {RAW_IMAGE_DIR}/2020/06/09/{item_id}/DrawObjPic/{filename}

    이미지 우선순위: question > explanation
    """
    images = item.get('images', {})

    # question 이미지 우선, 없으면 explanation 이미지 사용
    image_candidates = images.get('question', []) or images.get('explanation', [])

    if not image_candidates:
        return None

    # 첫 번째 이미지 사용
    img_path = image_candidates[0]  # e.g., "E8A959E.../DrawObjPic/P0697DA38.png"

    # 직접 경로 시도
    direct_path = RAW_IMAGE_DIR / img_path
    if direct_path.exists():
        return direct_path

    for folder in RAW_IMAGE_DIR.iterdir():
        if not folder.is_dir() or not folder.name.isdigit():
            continue

        if len(folder.name) == 8:
            # YYYYMMDD 구조 (예: 20150226)
            candidate = folder / img_path
            if candidate.exists():
                return candidate
        elif len(folder.name) == 4:
            # YYYY/MM/DD 구조 (예: 2020/06/09)
            for month_folder in folder.iterdir():
                if not month_folder.is_dir():
                    continue
                for day_folder in month_folder.iterdir():
                    if not day_folder.is_dir():
                        continue
                    candidate = day_folder / img_path
                    if candidate.exists():
                        return candidate

    return None


def generate_embeddings_batch(model, items, batch_size=4):
    """배치 단위로 멀티모달 임베딩 생성"""
    all_embeddings = {}
    errors = []

    for i in tqdm(range(0, len(items), batch_size), desc="Generating embeddings"):
        batch_items = items[i:i + batch_size]
        batch_inputs = []

        for item in batch_items:
            try:
                # 텍스트 준비
                text = prepare_text_input(item)

                # 멀티모달 입력 구성
                inp = {"text": text}

                # 이미지가 있는 문항은 이미지 포함
                if item.get('has_image'):
                    image_path = find_image_path(item)
                    if image_path and image_path.exists():
                        inp["image"] = str(image_path)

                batch_inputs.append((item['id'], inp))
            except Exception as e:
                errors.append({"id": item['id'], "error": str(e)})

        if not batch_inputs:
            continue

        try:
            # Qwen3VLEmbedder.process()로 배치 임베딩 생성
            inputs_for_model = [inp for _, inp in batch_inputs]
            embeddings = model.process(inputs_for_model, normalize=True)

            # 결과 저장
            for idx, (item_id, _) in enumerate(batch_inputs):
                all_embeddings[item_id] = embeddings[idx].cpu().numpy().tolist()

        except Exception as e:
            # 배치 실패 시 개별 처리
            print(f"\nBatch failed, processing individually: {e}")
            for item_id, inp in batch_inputs:
                try:
                    embedding = model.process([inp], normalize=True)
                    all_embeddings[item_id] = embedding[0].cpu().numpy().tolist()
                except Exception as e2:
                    errors.append({"id": item_id, "error": str(e2)})

    return all_embeddings, errors

def main():
    print("=" * 60)
    print("Qwen3-VL-Embedding-2B 멀티모달 임베딩 생성")
    print("=" * 60)

    # 모델 로드
    print("\n[1/4] 모델 로드 (Qwen3VLEmbedder)...")
    model = load_model()

    # 데이터 로드
    print("\n[2/4] 테스트 데이터 로드...")
    items = load_test_items()
    print(f"      문항 수: {len(items)}")

    # 이미지 문항 통계
    image_items = [item for item in items if item.get('has_image')]
    text_only_items = [item for item in items if not item.get('has_image')]
    print(f"      이미지 문항: {len(image_items)}")
    print(f"      텍스트 문항: {len(text_only_items)}")

    # 이미지 경로 확인
    found_images = 0
    for item in image_items:
        if find_image_path(item):
            found_images += 1
    print(f"      이미지 파일 발견: {found_images}/{len(image_items)}")

    # 임베딩 생성 (배치 처리)
    print("\n[3/4] 멀티모달 임베딩 생성...")
    embeddings, errors = generate_embeddings_batch(model, items, batch_size=4)

    print(f"\n      성공: {len(embeddings)}/{len(items)}")
    if errors:
        print(f"      오류: {len(errors)}")
        for err in errors[:5]:
            print(f"        - {err['id']}: {err['error']}")

    # 저장
    print("\n[4/4] 저장...")
    output_data = {
        "metadata": {
            "model": "Qwen3-VL-Embedding-2B",
            "mode": "multimodal",
            "total_items": len(items),
            "successful": len(embeddings),
            "failed": len(errors),
            "image_items": len(image_items),
            "images_found": found_images,
            "embedding_dim": 2048,
            "dtype": "float16"
        },
        "embeddings": embeddings,
        "errors": errors
    }

    output_file = OUTPUT_DIR / "qwen_embeddings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)

    print(f"      저장: {output_file}")

    # NumPy 형식으로도 저장 (빠른 로드용)
    np_file = OUTPUT_DIR / "qwen_embeddings.npz"
    ids = list(embeddings.keys())
    vectors = np.array([embeddings[id] for id in ids])
    np.savez(np_file, ids=ids, embeddings=vectors)
    print(f"      저장: {np_file}")

    # 메모리 정리
    del model
    gc.collect()
    torch.cuda.empty_cache()

    print("\n" + "=" * 60)
    print("멀티모달 임베딩 생성 완료!")
    print(f"Embedding shape: ({len(embeddings)}, 2048)")
    print("=" * 60)

if __name__ == "__main__":
    main()
