#!/usr/bin/env python3
"""
이미지 전용 검색 디버깅 - 왜 0%인지 분석
"""
import json
import sys
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-embedding-2b"
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")

sys.path.insert(0, str(MODEL_PATH / "scripts"))


def find_image_path(item_id):
    """문항 ID에 해당하는 이미지 경로 찾기"""
    for date_dir in RAW_IMAGE_DIR.iterdir():
        if not date_dir.is_dir():
            continue
        item_dir = date_dir / item_id
        if item_dir.exists():
            for img_file in item_dir.rglob("*.png"):
                return str(img_file)
            for img_file in item_dir.rglob("*.jpg"):
                return str(img_file)

    for year_dir in RAW_IMAGE_DIR.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        if len(year_dir.name) == 4:
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                for day_dir in month_dir.iterdir():
                    if not day_dir.is_dir():
                        continue
                    item_dir = day_dir / item_id
                    if item_dir.exists():
                        for img_file in item_dir.rglob("*.png"):
                            return str(img_file)
                        for img_file in item_dir.rglob("*.jpg"):
                            return str(img_file)
    return None


def load_image_gt():
    gt_path = DATA_DIR / "ground_truth_image.json"
    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["ground_truth"], data["metadata"]


def load_full_embeddings():
    emb_path = RESULTS_DIR / "qwen_embeddings_all_subjects_2b_multimodal.npz"
    data = np.load(emb_path, allow_pickle=True)
    return data['embeddings'], data['ids']


def main():
    print("=" * 60)
    print("Image-Only 검색 디버깅")
    print("=" * 60)

    # Load embeddings
    print("\n[1] 임베딩 로드 중...")
    corpus_embs, corpus_ids = load_full_embeddings()
    id_to_idx = {str(id_): idx for idx, id_ in enumerate(corpus_ids)}
    print(f"전체 임베딩: {len(corpus_ids):,}개")

    # Load GT
    print("\n[2] Ground Truth 로드 중...")
    ground_truth, _ = load_image_gt()
    print(f"Image GT: {len(ground_truth)} queries")

    # Analyze first 3 queries
    print("\n[3] 첫 3개 쿼리 분석...")

    from qwen3_vl_embedding import Qwen3VLForEmbedding
    from transformers.models.qwen3_vl.processing_qwen3_vl import Qwen3VLProcessor
    from qwen_vl_utils.vision_process import process_vision_info

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Qwen3VLForEmbedding.from_pretrained(
        str(MODEL_PATH), trust_remote_code=True, torch_dtype=torch.float16
    ).to(device)
    processor = Qwen3VLProcessor.from_pretrained(str(MODEL_PATH), padding_side='right')
    model.eval()

    instruction = "Represent this educational question image for retrieval."

    for i, gt in enumerate(ground_truth[:3]):
        query_id = gt["query_id"]
        relevant_ids = {item["id"] for item in gt["relevant_items"]}

        print(f"\n{'='*60}")
        print(f"Query {i+1}: {query_id}")
        print(f"Expected relevant items: {relevant_ids}")

        # Check if query exists in corpus
        if query_id in id_to_idx:
            query_idx = id_to_idx[query_id]
            print(f"Query in corpus: idx={query_idx}")

            # Get multimodal embedding for this query (from corpus)
            query_mm_emb = corpus_embs[query_idx]

            # Check if relevant items exist in corpus
            for rel_id in relevant_ids:
                if rel_id in id_to_idx:
                    rel_idx = id_to_idx[rel_id]
                    rel_emb = corpus_embs[rel_idx]
                    sim = np.dot(query_mm_emb, rel_emb)
                    print(f"  Relevant {rel_id}: idx={rel_idx}, similarity={sim:.4f}")
                else:
                    print(f"  Relevant {rel_id}: NOT in corpus!")
        else:
            print(f"Query NOT in corpus!")

        # Find image path
        image_path = find_image_path(query_id)
        if not image_path:
            print("Image not found!")
            continue
        print(f"Image path: {image_path}")

        # Generate image-only embedding
        content = [{
            'type': 'image', 'image': 'file://' + image_path,
            "min_pixels": 4 * 32 * 32,
            "max_pixels": 1800 * 32 * 32
        }]
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": instruction}]},
            {"role": "user", "content": content}
        ]

        text_input = processor.apply_chat_template(
            [conversation], add_generation_prompt=True, tokenize=False
        )

        try:
            images, video_inputs, video_kwargs = process_vision_info(
                [conversation], image_patch_size=16,
                return_video_metadata=True, return_video_kwargs=True
            )
        except Exception as e:
            print(f"Vision processing error: {e}")
            continue

        with torch.no_grad():
            inputs = processor(
                text=text_input,
                images=images if images else None,
                videos=video_inputs if video_inputs else None,
                padding=True,
                return_tensors="pt",
                **video_kwargs
            ).to(device)

            outputs = model(**inputs)
            last_hidden_state = outputs.last_hidden_state

            # Mean pooling
            attention_mask = inputs["attention_mask"]
            mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
            sum_embeddings = torch.sum(last_hidden_state * mask_expanded, dim=1)
            sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
            embedding = sum_embeddings / sum_mask
            embedding = F.normalize(embedding, p=2, dim=-1)
            query_img_emb = embedding.squeeze().cpu().numpy()

        # Compare image-only vs multimodal embedding
        if query_id in id_to_idx:
            query_mm_emb = corpus_embs[id_to_idx[query_id]]
            self_sim = np.dot(query_img_emb, query_mm_emb)
            print(f"\nImage-Only vs Multimodal similarity (same item): {self_sim:.4f}")

        # Search with image-only embedding
        similarities = np.dot(corpus_embs, query_img_emb)
        top_indices = np.argsort(similarities)[::-1][:15]

        print(f"\nTop 15 results (Image-Only query):")
        found_relevant = False
        for rank, idx in enumerate(top_indices, 1):
            item_id = corpus_ids[idx]
            score = similarities[idx]
            is_relevant = "✓ RELEVANT" if item_id in relevant_ids else ""
            is_self = "(SELF)" if item_id == query_id else ""
            if item_id in relevant_ids:
                found_relevant = True
            print(f"  {rank:2d}. {item_id} | score={score:.4f} {is_self} {is_relevant}")

        if not found_relevant:
            print("\n  ⚠️ No relevant items in top 15!")

    print("\n" + "=" * 60)
    print("분석 완료")


if __name__ == "__main__":
    main()
