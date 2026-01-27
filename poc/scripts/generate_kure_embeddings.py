#!/usr/bin/env python3
"""
Task #9: KURE-v1 텍스트 임베딩 생성
한국어 텍스트 전용 임베딩 (baseline)
"""
import json
import numpy as np
from pathlib import Path
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/kure-v1"
DATA_DIR = POC_DIR / "data"
OUTPUT_DIR = POC_DIR / "results"

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
            choices_text += f" {i}. {choice}"

    # 전체 텍스트
    text = f"{question}{choices_text}"

    return text

def main():
    print("=" * 60)
    print("KURE-v1 텍스트 임베딩 생성")
    print("=" * 60)

    # 모델 로드
    print("\n[1/4] 모델 로드...")
    model = SentenceTransformer(str(MODEL_PATH))
    print(f"      Model loaded: {MODEL_PATH.name}")
    print(f"      Embedding dimension: {model.get_sentence_embedding_dimension()}")

    # 데이터 로드
    print("\n[2/4] 테스트 데이터 로드...")
    items = load_test_items()
    print(f"      문항 수: {len(items)}")

    # 텍스트 준비
    print("\n[3/4] 임베딩 생성...")
    texts = []
    ids = []
    for item in items:
        text = prepare_text_input(item)
        texts.append(text)
        ids.append(item['id'])

    # 배치 임베딩 생성
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    print(f"      Embedding shape: {embeddings.shape}")

    # 저장
    print("\n[4/4] 저장...")

    # JSON 형식
    embeddings_dict = {id: emb.tolist() for id, emb in zip(ids, embeddings)}
    output_data = {
        "metadata": {
            "model": "KURE-v1",
            "total_items": len(items),
            "embedding_dim": embeddings.shape[1],
        },
        "embeddings": embeddings_dict
    }

    output_file = OUTPUT_DIR / "kure_embeddings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
    print(f"      저장: {output_file}")

    # NumPy 형식
    np_file = OUTPUT_DIR / "kure_embeddings.npz"
    np.savez(np_file, ids=ids, embeddings=embeddings)
    print(f"      저장: {np_file}")

    print("\n" + "=" * 60)
    print("KURE-v1 임베딩 생성 완료!")
    print(f"Embedding shape: {embeddings.shape}")
    print("=" * 60)

if __name__ == "__main__":
    main()
