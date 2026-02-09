#!/usr/bin/env python3
"""
8B VL vs 2B 전체 임베딩 공정 비교
- GT에 포함된 문항만 필터링하여 평가
- 동일 조건에서 8B VL과 2B 멀티모달 비교
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import datetime


POC_DIR = Path(__file__).parent.parent
RESULTS_DIR = POC_DIR / "results"
DATA_DIR = POC_DIR / "data"


def load_embeddings(file_path):
    """임베딩 파일 로드"""
    with open(file_path) as f:
        data = json.load(f)

    if "embeddings" in data:
        embeddings = data["embeddings"]
    else:
        embeddings = data

    meta = data.get("metadata", {})
    return embeddings, meta


def load_ground_truth(gt_name):
    """Ground Truth 로드"""
    gt_path = DATA_DIR / f"ground_truth_{gt_name}.json"
    with open(gt_path) as f:
        return json.load(f)


def get_gt_item_ids(gt_data):
    """GT에서 모든 관련 item ID 추출"""
    item_ids = set()
    for gt_item in gt_data["ground_truth"]:
        item_ids.add(gt_item["query_id"])
        for rel in gt_item["relevant_items"]:
            item_ids.add(rel["id"])
    return item_ids


def filter_embeddings(embeddings, item_ids):
    """지정된 ID만 포함하도록 임베딩 필터링"""
    return {k: v for k, v in embeddings.items() if k in item_ids}


def compute_similarity_matrix(embeddings):
    """코사인 유사도 행렬 계산"""
    item_ids = list(embeddings.keys())
    emb_matrix = np.array([embeddings[item_id] for item_id in item_ids])

    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    emb_matrix_normalized = emb_matrix / (norms + 1e-10)
    similarity_matrix = emb_matrix_normalized @ emb_matrix_normalized.T

    return item_ids, similarity_matrix


def get_rankings(item_ids, similarity_matrix, query_id, top_k=20):
    """쿼리에 대한 Top-K 결과"""
    if query_id not in item_ids:
        return []

    query_idx = item_ids.index(query_id)
    similarities = similarity_matrix[query_idx].copy()
    similarities[query_idx] = -np.inf

    top_indices = np.argsort(-similarities)[:top_k]
    return [(item_ids[idx], float(similarities[idx])) for idx in top_indices]


def top_k_recall(predictions, ground_truth, k):
    """Top-K Recall"""
    pred_ids = [p[0] for p in predictions[:k]]
    relevant_ids = set(ground_truth.keys())
    hits = len(set(pred_ids) & relevant_ids)
    return hits / len(relevant_ids) if relevant_ids else 0


def mrr(predictions, ground_truth):
    """MRR"""
    for i, (pred_id, _) in enumerate(predictions):
        if pred_id in ground_truth:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_embeddings(embeddings, gt_data, name):
    """임베딩 평가"""
    item_ids, similarity_matrix = compute_similarity_matrix(embeddings)

    metrics = {'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [], 'mrr': []}
    by_category = defaultdict(lambda: defaultdict(list))

    for gt_item in gt_data["ground_truth"]:
        query_id = gt_item["query_id"]
        category = gt_item.get("query_category", "unknown")
        relevant = {item["id"]: item.get("relevance", 1) for item in gt_item["relevant_items"]}

        if not relevant or query_id not in item_ids:
            continue

        predictions = get_rankings(item_ids, similarity_matrix, query_id, top_k=20)

        metrics['top_1'].append(top_k_recall(predictions, relevant, 1))
        metrics['top_3'].append(top_k_recall(predictions, relevant, 3))
        metrics['top_5'].append(top_k_recall(predictions, relevant, 5))
        metrics['top_10'].append(top_k_recall(predictions, relevant, 10))
        metrics['mrr'].append(mrr(predictions, relevant))

        by_category[category]['top_5'].append(top_k_recall(predictions, relevant, 5))
        by_category[category]['mrr'].append(mrr(predictions, relevant))

    return {
        'name': name,
        'total_queries': len(metrics['top_1']),
        'metrics': {k: float(np.mean(v)) * 100 for k, v in metrics.items()},
        'by_category': {
            cat: {k: float(np.mean(v)) * 100 for k, v in cat_metrics.items()}
            for cat, cat_metrics in by_category.items()
        }
    }


def print_table(results, gt_name):
    """결과 테이블 출력"""
    print(f"\n{'='*90}")
    print(f"  {gt_name} 기준 성능 비교")
    print(f"{'='*90}")
    print(f"{'모델':<35} | {'Top-1':>8} | {'Top-3':>8} | {'Top-5':>8} | {'Top-10':>8} | {'MRR':>8}")
    print("-"*90)

    for result in results:
        m = result['metrics']
        print(f"{result['name']:<35} | {m['top_1']:>7.1f}% | {m['top_3']:>7.1f}% | {m['top_5']:>7.1f}% | {m['top_10']:>7.1f}% | {m['mrr']:>7.1f}%")

    best = max(results, key=lambda x: x['metrics']['top_5'])
    print("-"*90)
    print(f"🏆 Top-5 최고: {best['name']} ({best['metrics']['top_5']:.1f}%)")


def main():
    print("="*90)
    print("  8B VL vs 2B 전체 임베딩 공정 비교")
    print("  (GT 포함 문항만 필터링하여 동일 조건 평가)")
    print("="*90)

    # 전체 임베딩 파일
    embedding_files = {
        "2B 멀티모달 (전체 10,951개 기반)": RESULTS_DIR / "qwen_embeddings_full_2b_multimodal.json",
        "8B VL (전체 10,952개 기반)": RESULTS_DIR / "qwen_vl_embeddings_full_8b.json",
    }

    # 임베딩 로드
    print("\n[1/4] 전체 임베딩 로드...")
    full_embeddings = {}
    for name, path in embedding_files.items():
        if path.exists():
            emb, meta = load_embeddings(path)
            full_embeddings[name] = emb
            dim = len(list(emb.values())[0])
            print(f"  ✓ {name}: {len(emb):,}개, {dim}차원")
        else:
            print(f"  ✗ {name}: 파일 없음")

    # GT 로드
    print("\n[2/4] Ground Truth 로드...")
    gt_types = {
        "Image GT": "image",
        "Hybrid GT": "hybrid",
    }

    gt_data_dict = {}
    for gt_name, gt_file in gt_types.items():
        try:
            gt_data_dict[gt_name] = load_ground_truth(gt_file)
            n_queries = len(gt_data_dict[gt_name]["ground_truth"])
            print(f"  ✓ {gt_name}: {n_queries} 쿼리")
        except FileNotFoundError:
            print(f"  ✗ {gt_name}: 파일 없음")

    # 평가
    print("\n[3/4] GT 기준 필터링 후 평가...")
    all_results = {}

    for gt_name, gt_data in gt_data_dict.items():
        gt_items = get_gt_item_ids(gt_data)
        print(f"\n  [{gt_name}] GT 관련 문항: {len(gt_items)}개")

        results = []
        for emb_name, full_emb in full_embeddings.items():
            # GT 문항만 필터링
            filtered_emb = filter_embeddings(full_emb, gt_items)
            result = evaluate_embeddings(filtered_emb, gt_data, emb_name)
            results.append(result)
            print(f"    ✓ {emb_name}: 필터링 {len(filtered_emb)}개 → Top-5 = {result['metrics']['top_5']:.1f}%")

        all_results[gt_name] = results
        print_table(results, gt_name)

    # 결과 저장
    print("\n[4/4] 결과 저장...")
    output = {
        "metadata": {
            "description": "8B VL vs 2B 전체 임베딩 공정 비교",
            "method": "GT 포함 문항만 필터링하여 동일 조건 평가",
            "created_at": datetime.now().isoformat(),
            "models": {
                "2B": "Qwen3-VL-Embedding-2B (멀티모달, 2048 dim)",
                "8B VL": "Qwen3-VL-Embedding-8B (멀티모달, 4096 dim)"
            }
        },
        "results": {
            gt_name: {r['name']: r for r in results}
            for gt_name, results in all_results.items()
        }
    }

    output_path = RESULTS_DIR / "8b_vl_vs_2b_full_comparison.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  저장: {output_path}")

    # 결론
    print("\n" + "="*90)
    print("  📊 결론")
    print("="*90)

    for gt_name, results in all_results.items():
        r2b = next((r for r in results if "2B" in r['name']), None)
        r8b = next((r for r in results if "8B" in r['name']), None)

        if r2b and r8b:
            diff = r8b['metrics']['top_5'] - r2b['metrics']['top_5']
            winner = "8B VL" if diff > 0 else "2B"
            print(f"\n  [{gt_name}]")
            print(f"    2B:   Top-5 = {r2b['metrics']['top_5']:.1f}%  MRR = {r2b['metrics']['mrr']:.1f}%")
            print(f"    8B VL: Top-5 = {r8b['metrics']['top_5']:.1f}%  MRR = {r8b['metrics']['mrr']:.1f}%")
            print(f"    → 차이: {diff:+.1f}%p ({winner} 승)")

    print("\n" + "="*90)


if __name__ == "__main__":
    main()
