#!/usr/bin/env python3
"""
Task #10: SigLIP 이미지 임베딩 생성
이미지 전용 임베딩 (baseline)
"""
import json
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm
from PIL import Image
from transformers import SiglipImageProcessor, SiglipModel

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/siglip-base"
DATA_DIR = POC_DIR / "data"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")
OUTPUT_DIR = POC_DIR / "results"

def load_test_items():
    """테스트 데이터 로드"""
    with open(DATA_DIR / "test_items.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['items']

def find_image_path(item):
    """문항의 이미지 경로 찾기"""
    images = item.get('images', {})
    question_images = images.get('question', [])

    if not question_images:
        return None

    # 이미지 경로에서 파일명 추출
    img_rel_path = question_images[0]  # e.g., "ID/DrawObjPic/filename.png"
    item_id = item['id']

    # 방법 1: 재귀적으로 ID 폴더 찾기
    import subprocess
    try:
        result = subprocess.run(
            ['find', str(RAW_IMAGE_DIR), '-type', 'd', '-name', item_id],
            capture_output=True, text=True, timeout=10
        )
        if result.stdout.strip():
            item_folder = Path(result.stdout.strip().split('\n')[0])
            # img_rel_path에서 ID 부분 제거하고 나머지 경로 사용
            img_filename = img_rel_path.split('/')[-1]
            full_path = item_folder / "DrawObjPic" / img_filename
            if full_path.exists():
                return full_path
    except Exception:
        pass

    return None

def main():
    print("=" * 60)
    print("SigLIP 이미지 임베딩 생성")
    print("=" * 60)

    # 모델 로드
    print("\n[1/4] 모델 로드...")
    processor = SiglipImageProcessor.from_pretrained(MODEL_PATH)
    model = SiglipModel.from_pretrained(MODEL_PATH)
    model.eval()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    print(f"      Model loaded on: {device}")

    # 데이터 로드
    print("\n[2/4] 테스트 데이터 로드...")
    items = load_test_items()
    print(f"      문항 수: {len(items)}")

    # 이미지 포함 문항 필터링
    image_items = [item for item in items if item.get('has_image', False)]
    print(f"      이미지 포함 문항: {len(image_items)}")

    # 임베딩 생성
    print("\n[3/4] 임베딩 생성...")
    embeddings = {}
    errors = []

    for item in tqdm(image_items, desc="Processing images"):
        item_id = item['id']
        image_path = find_image_path(item)

        if not image_path:
            errors.append({"id": item_id, "error": "Image not found"})
            continue

        try:
            # 이미지 로드
            image = Image.open(image_path).convert("RGB")

            # 전처리
            inputs = processor(images=image, return_tensors="pt")
            inputs = {k: v.to(device) for k, v in inputs.items()}

            # 임베딩 생성
            with torch.no_grad():
                outputs = model.vision_model(**inputs)
                # Use pooler output or mean of last hidden state
                pooled = outputs.pooler_output if outputs.pooler_output is not None else outputs.last_hidden_state.mean(dim=1)

            # 정규화
            embedding = pooled / pooled.norm(p=2, dim=-1, keepdim=True)
            embeddings[item_id] = embedding.cpu().numpy()[0].tolist()

        except Exception as e:
            errors.append({"id": item_id, "error": str(e)})

    print(f"\n      성공: {len(embeddings)}/{len(image_items)}")
    if errors:
        print(f"      오류: {len(errors)}")

    # 이미지 없는 문항은 zero vector
    embedding_dim = 768  # SigLIP-base dimension
    for item in items:
        if item['id'] not in embeddings:
            embeddings[item['id']] = [0.0] * embedding_dim

    # 저장
    print("\n[4/4] 저장...")

    output_data = {
        "metadata": {
            "model": "SigLIP-base",
            "total_items": len(items),
            "image_items": len(image_items),
            "successful": len([e for e in embeddings.values() if sum(e) != 0]),
            "embedding_dim": embedding_dim,
        },
        "embeddings": embeddings,
        "errors": errors
    }

    output_file = OUTPUT_DIR / "siglip_embeddings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
    print(f"      저장: {output_file}")

    # NumPy 형식
    ids = list(embeddings.keys())
    vectors = np.array([embeddings[id] for id in ids])
    np_file = OUTPUT_DIR / "siglip_embeddings.npz"
    np.savez(np_file, ids=ids, embeddings=vectors)
    print(f"      저장: {np_file}")

    print("\n" + "=" * 60)
    print("SigLIP 임베딩 생성 완료!")
    print(f"Embedding shape: ({len(embeddings)}, {embedding_dim})")
    print("=" * 60)

if __name__ == "__main__":
    main()
