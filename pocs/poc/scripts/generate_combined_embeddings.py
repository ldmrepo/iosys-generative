#!/usr/bin/env python3
"""
Task #11: KURE+SigLIP 결합 임베딩 생성
텍스트 (KURE-v1) + 이미지 (SigLIP) 결합 임베딩
"""
import json
import numpy as np
from pathlib import Path

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
RESULTS_DIR = POC_DIR / "results"

def main():
    print("=" * 60)
    print("KURE+SigLIP 결합 임베딩 생성")
    print("=" * 60)

    # KURE 임베딩 로드
    print("\n[1/4] KURE-v1 임베딩 로드...")
    with open(RESULTS_DIR / "kure_embeddings.json", 'r') as f:
        kure_data = json.load(f)
    kure_embeddings = kure_data['embeddings']
    print(f"      KURE dimension: {len(list(kure_embeddings.values())[0])}")

    # SigLIP 임베딩 로드
    print("\n[2/4] SigLIP 임베딩 로드...")
    with open(RESULTS_DIR / "siglip_embeddings.json", 'r') as f:
        siglip_data = json.load(f)
    siglip_embeddings = siglip_data['embeddings']
    print(f"      SigLIP dimension: {len(list(siglip_embeddings.values())[0])}")

    # 결합 임베딩 생성
    print("\n[3/4] 결합 임베딩 생성...")
    combined_embeddings = {}

    for item_id in kure_embeddings.keys():
        kure_emb = np.array(kure_embeddings[item_id])
        siglip_emb = np.array(siglip_embeddings.get(item_id, [0.0] * 768))

        # Concatenation (KURE 1024 + SigLIP 768 = 1792)
        combined = np.concatenate([kure_emb, siglip_emb])

        # L2 정규화
        combined = combined / np.linalg.norm(combined)

        combined_embeddings[item_id] = combined.tolist()

    print(f"      Combined dimension: {len(list(combined_embeddings.values())[0])}")

    # 저장
    print("\n[4/4] 저장...")
    output_data = {
        "metadata": {
            "model": "KURE-v1 + SigLIP",
            "method": "concatenation + L2 normalization",
            "total_items": len(combined_embeddings),
            "embedding_dim": 1792,
            "kure_dim": 1024,
            "siglip_dim": 768
        },
        "embeddings": combined_embeddings
    }

    output_file = RESULTS_DIR / "combined_embeddings.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False)
    print(f"      저장: {output_file}")

    # NumPy 형식
    ids = list(combined_embeddings.keys())
    vectors = np.array([combined_embeddings[id] for id in ids])
    np_file = RESULTS_DIR / "combined_embeddings.npz"
    np.savez(np_file, ids=ids, embeddings=vectors)
    print(f"      저장: {np_file}")

    print("\n" + "=" * 60)
    print("결합 임베딩 생성 완료!")
    print(f"Embedding shape: ({len(combined_embeddings)}, 1792)")
    print("=" * 60)

if __name__ == "__main__":
    main()
