#!/usr/bin/env python3
"""
이미지 전용 검색 평가 (Image-Only Query Search)
- 쿼리: 이미지만 사용 (텍스트 제외)
- 대상: 전체 임베딩 (텍스트+이미지)
- Ground Truth: Image GT (GPT-4o 평가 기반)
"""
import json
import sys
import torch
import torch.nn.functional as F
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-embedding-2b"
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")

# Add model scripts to path
sys.path.insert(0, str(MODEL_PATH / "scripts"))


def find_image_path(item_id):
    """문항 ID에 해당하는 이미지 경로 찾기"""
    # YYYYMMDD 형식 검색
    for date_dir in RAW_IMAGE_DIR.iterdir():
        if not date_dir.is_dir():
            continue
        item_dir = date_dir / item_id
        if item_dir.exists():
            for img_file in item_dir.rglob("*.png"):
                return str(img_file)
            for img_file in item_dir.rglob("*.jpg"):
                return str(img_file)

    # YYYY/MM/DD 형식 검색
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


class Qwen3VLEmbedderImageOnly:
    """이미지 전용 임베딩 생성기 (Mean Pooling)"""

    def __init__(self, model_name_or_path, **kwargs):
        from qwen3_vl_embedding import Qwen3VLForEmbedding
        from transformers.models.qwen3_vl.processing_qwen3_vl import Qwen3VLProcessor

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = Qwen3VLForEmbedding.from_pretrained(
            model_name_or_path, trust_remote_code=True, **kwargs
        ).to(device)
        self.processor = Qwen3VLProcessor.from_pretrained(
            model_name_or_path, padding_side='right'
        )
        self.model.eval()
        self.default_instruction = "Represent this educational question image for retrieval."

    def format_input(self, image):
        """이미지만 입력으로 구성"""
        content = []
        conversation = [
            {"role": "system", "content": [{"type": "text", "text": self.default_instruction}]},
            {"role": "user", "content": content}
        ]

        if image:
            image_content = image if image.startswith(('http', 'oss')) else 'file://' + image
            content.append({
                'type': 'image', 'image': image_content,
                "min_pixels": 4 * 32 * 32,
                "max_pixels": 1800 * 32 * 32
            })
        else:
            content.append({'type': 'text', 'text': "NULL"})

        return conversation

    @torch.no_grad()
    def process_single(self, image, normalize=True):
        """이미지만으로 임베딩 생성"""
        from qwen_vl_utils.vision_process import process_vision_info

        conversation = self.format_input(image=image)

        text_input = self.processor.apply_chat_template(
            [conversation], add_generation_prompt=True, tokenize=False
        )

        try:
            images, video_inputs, video_kwargs = process_vision_info(
                [conversation], image_patch_size=16,
                return_video_metadata=True, return_video_kwargs=True
            )
        except Exception as e:
            print(f"Error processing image: {e}")
            return None

        inputs = self.processor(
            text=text_input,
            images=images if images else None,
            videos=video_inputs if video_inputs else None,
            padding=True,
            return_tensors="pt",
            **video_kwargs
        ).to(self.model.device)

        outputs = self.model(**inputs)
        last_hidden_state = outputs.last_hidden_state

        # Mean pooling
        attention_mask = inputs["attention_mask"]
        mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        sum_embeddings = torch.sum(last_hidden_state * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        embedding = sum_embeddings / sum_mask

        if normalize:
            embedding = F.normalize(embedding, p=2, dim=-1)

        return embedding.squeeze().cpu().numpy()


def load_image_gt():
    """Image Ground Truth 로드"""
    gt_path = DATA_DIR / "ground_truth_image.json"
    with open(gt_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["ground_truth"], data["metadata"]


def load_full_embeddings():
    """전체 임베딩 로드"""
    emb_path = RESULTS_DIR / "qwen_embeddings_all_subjects_2b_multimodal.npz"
    data = np.load(emb_path, allow_pickle=True)
    embeddings = data['embeddings']
    ids = data['ids']
    return embeddings, ids


def cosine_search(query_emb, corpus_embs, top_k=10):
    """코사인 유사도 기반 검색"""
    query_emb = query_emb.reshape(1, -1)
    similarities = np.dot(corpus_embs, query_emb.T).squeeze()
    top_indices = np.argsort(similarities)[::-1][:top_k]
    return top_indices, similarities[top_indices]


def evaluate_retrieval(predictions, ground_truth):
    """검색 결과 평가"""
    metrics = {"top_1": 0, "top_3": 0, "top_5": 0, "top_10": 0, "mrr": 0}
    total = 0

    for query_id, pred_ids in predictions.items():
        # Find relevant items for this query
        relevant_ids = set()
        for gt in ground_truth:
            if gt["query_id"] == query_id:
                relevant_ids = {item["id"] for item in gt["relevant_items"]}
                break

        if not relevant_ids:
            continue

        total += 1

        # Calculate metrics
        for k, key in [(1, "top_1"), (3, "top_3"), (5, "top_5"), (10, "top_10")]:
            if any(pid in relevant_ids for pid in pred_ids[:k]):
                metrics[key] += 1

        # MRR
        for rank, pid in enumerate(pred_ids, 1):
            if pid in relevant_ids:
                metrics["mrr"] += 1 / rank
                break

    # Convert to percentages
    if total > 0:
        for key in metrics:
            metrics[key] = (metrics[key] / total) * 100

    metrics["total_queries"] = total
    return metrics


def main():
    print("=" * 60)
    print("이미지 전용 검색 평가 (Image-Only Query)")
    print("=" * 60)

    # Load model
    print("\n[1/4] 모델 로드 중...")
    embedder = Qwen3VLEmbedderImageOnly(
        str(MODEL_PATH),
        torch_dtype=torch.float16
    )
    print("모델 로드 완료")

    # Load ground truth
    print("\n[2/4] Ground Truth 로드 중...")
    ground_truth, gt_meta = load_image_gt()
    print(f"Image GT: {len(ground_truth)} queries")

    # Load full embeddings
    print("\n[3/4] 전체 임베딩 로드 중...")
    corpus_embs, corpus_ids = load_full_embeddings()
    id_to_idx = {id_: idx for idx, id_ in enumerate(corpus_ids)}
    print(f"전체 임베딩: {len(corpus_ids):,}개")

    # Generate image-only query embeddings and search
    print("\n[4/4] 이미지 전용 검색 수행 중...")
    predictions = {}
    failed_queries = []

    for gt in tqdm(ground_truth, desc="Image-only search"):
        query_id = gt["query_id"]

        # Find image path
        image_path = find_image_path(query_id)
        if not image_path:
            failed_queries.append({"id": query_id, "reason": "image not found"})
            continue

        # Generate image-only embedding
        query_emb = embedder.process_single(image=image_path)
        if query_emb is None:
            failed_queries.append({"id": query_id, "reason": "embedding failed"})
            continue

        # Search
        top_indices, scores = cosine_search(query_emb, corpus_embs, top_k=10)
        pred_ids = [corpus_ids[idx] for idx in top_indices]

        # Exclude self
        pred_ids = [pid for pid in pred_ids if pid != query_id][:10]
        predictions[query_id] = pred_ids

    # Evaluate
    print("\n" + "=" * 60)
    print("평가 결과")
    print("=" * 60)

    metrics = evaluate_retrieval(predictions, ground_truth)

    print(f"\n총 쿼리: {metrics['total_queries']}개")
    print(f"실패: {len(failed_queries)}개")
    print(f"\n{'Metric':<10} {'Score':>10}")
    print("-" * 22)
    print(f"{'Top-1':<10} {metrics['top_1']:>9.1f}%")
    print(f"{'Top-3':<10} {metrics['top_3']:>9.1f}%")
    print(f"{'Top-5':<10} {metrics['top_5']:>9.1f}%")
    print(f"{'Top-10':<10} {metrics['top_10']:>9.1f}%")
    print(f"{'MRR':<10} {metrics['mrr']:>9.1f}%")

    # Compare with multimodal (text+image)
    print("\n" + "-" * 60)
    print("비교: Image-Only vs Multimodal (Text+Image)")
    print("-" * 60)

    # Load multimodal results for comparison
    multimodal_results_path = RESULTS_DIR / "2b_multimodal_full_evaluation.json"
    if multimodal_results_path.exists():
        with open(multimodal_results_path) as f:
            multimodal_data = json.load(f)
        mm_metrics = multimodal_data["results"]["image_gt"]

        print(f"\n{'Metric':<10} {'Image-Only':>12} {'Multimodal':>12} {'차이':>10}")
        print("-" * 48)
        for key in ["top_1", "top_3", "top_5", "top_10", "mrr"]:
            io_val = metrics[key]
            mm_val = mm_metrics[key]
            diff = io_val - mm_val
            diff_str = f"{diff:+.1f}%p"
            print(f"{key.upper():<10} {io_val:>11.1f}% {mm_val:>11.1f}% {diff_str:>10}")

    # Save results
    results = {
        "model": "Qwen3-VL-Embedding-2B",
        "mode": "image_only_query",
        "total_corpus": len(corpus_ids),
        "results": {
            "image_only": metrics,
            "failed_queries": failed_queries
        }
    }

    output_path = RESULTS_DIR / "image_only_search_evaluation.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")


if __name__ == "__main__":
    main()
