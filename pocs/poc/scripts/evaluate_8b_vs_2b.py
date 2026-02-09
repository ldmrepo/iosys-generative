#!/usr/bin/env python3
"""
8B vs 2B 임베딩 성능 비교 (CPU 전용)
- GPU 불필요: 사전 생성된 임베딩 파일 사용
- Image GT, Hybrid GT 기준 평가
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
    """임베딩 파일 로드 (다양한 포맷 지원)"""
    with open(file_path) as f:
        data = json.load(f)

    # 포맷 정규화
    if "embeddings" in data:
        embeddings = data["embeddings"]
    else:
        embeddings = data

    # 메타데이터 추출
    if "metadata" in data:
        meta = data["metadata"]
    else:
        meta = {k: v for k, v in data.items() if k != "embeddings"}

    return embeddings, meta


def load_ground_truth(gt_name):
    """Ground Truth 로드"""
    gt_path = DATA_DIR / f"ground_truth_{gt_name}.json"
    with open(gt_path) as f:
        return json.load(f)


def compute_similarity_matrix(embeddings):
    """코사인 유사도 행렬 계산"""
    item_ids = list(embeddings.keys())
    emb_matrix = np.array([embeddings[item_id] for item_id in item_ids])

    # L2 정규화
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    emb_matrix_normalized = emb_matrix / (norms + 1e-10)

    # 코사인 유사도 행렬
    similarity_matrix = emb_matrix_normalized @ emb_matrix_normalized.T

    return item_ids, similarity_matrix


def get_rankings(item_ids, similarity_matrix, query_id, top_k=20):
    """쿼리에 대한 Top-K 결과 반환"""
    if query_id not in item_ids:
        return []

    query_idx = item_ids.index(query_id)
    similarities = similarity_matrix[query_idx].copy()
    similarities[query_idx] = -np.inf  # 자기 자신 제외

    top_indices = np.argsort(-similarities)[:top_k]
    return [(item_ids[idx], float(similarities[idx])) for idx in top_indices]


def top_k_recall(predictions, ground_truth, k):
    """Top-K Recall 계산"""
    pred_ids = [p[0] for p in predictions[:k]]
    relevant_ids = set(ground_truth.keys())
    hits = len(set(pred_ids) & relevant_ids)
    return hits / len(relevant_ids) if relevant_ids else 0


def mrr(predictions, ground_truth):
    """MRR (Mean Reciprocal Rank) 계산"""
    for i, (pred_id, _) in enumerate(predictions):
        if pred_id in ground_truth:
            return 1.0 / (i + 1)
    return 0.0


def evaluate_embeddings(embeddings, gt_data, name):
    """임베딩 성능 평가"""
    item_ids, similarity_matrix = compute_similarity_matrix(embeddings)

    metrics = {
        'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [],
        'mrr': []
    }

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

    result = {
        'name': name,
        'total_queries': len(metrics['top_1']),
        'metrics': {k: float(np.mean(v)) * 100 for k, v in metrics.items()},
        'by_category': {
            cat: {k: float(np.mean(v)) * 100 for k, v in cat_metrics.items()}
            for cat, cat_metrics in by_category.items()
        }
    }

    return result


def print_comparison_table(results, gt_name):
    """비교 테이블 출력"""
    print(f"\n{'='*80}")
    print(f"  {gt_name} 기준 성능 비교")
    print(f"{'='*80}")
    print(f"{'모델':<30} | {'Top-1':>8} | {'Top-3':>8} | {'Top-5':>8} | {'Top-10':>8} | {'MRR':>8}")
    print("-"*80)

    for result in results:
        m = result['metrics']
        print(f"{result['name']:<30} | {m['top_1']:>7.1f}% | {m['top_3']:>7.1f}% | {m['top_5']:>7.1f}% | {m['top_10']:>7.1f}% | {m['mrr']:>7.1f}%")

    # 최고 성능 표시
    best_top5 = max(results, key=lambda x: x['metrics']['top_5'])
    print("-"*80)
    print(f"🏆 Top-5 최고: {best_top5['name']} ({best_top5['metrics']['top_5']:.1f}%)")


def main():
    print("="*80)
    print("  8B vs 2B 임베딩 성능 비교 (CPU 전용)")
    print("="*80)

    # 임베딩 파일 목록 (전체 데이터셋 우선)
    embedding_files = {
        "2B 멀티모달 전체 (mean)": RESULTS_DIR / "qwen_embeddings_full_2b_multimodal.json",
        "8B VL 전체 (mean)": RESULTS_DIR / "qwen_vl_embeddings_full_8b.json",
        "2B 멀티모달 100개 (mean)": RESULTS_DIR / "qwen_embeddings_multimodal_meanpool.json",
        "2B 텍스트 100개 (mean)": RESULTS_DIR / "qwen_embeddings_textonly.json",
        "8B VL 100개 (mean)": RESULTS_DIR / "qwen_vl_embeddings_8b.json",
    }

    # 임베딩 로드
    print("\n임베딩 로드 중...")
    embeddings_dict = {}
    for name, path in embedding_files.items():
        if path.exists():
            emb, meta = load_embeddings(path)
            embeddings_dict[name] = emb
            dim = len(list(emb.values())[0])
            print(f"  ✓ {name}: {len(emb)}개, {dim}차원")
        else:
            print(f"  ✗ {name}: 파일 없음")

    # Ground Truth 로드
    print("\nGround Truth 로드 중...")
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

    # 평가 실행
    all_results = {}

    for gt_name, gt_data in gt_data_dict.items():
        print(f"\n{gt_name} 평가 중...")
        results = []

        for emb_name, embeddings in embeddings_dict.items():
            result = evaluate_embeddings(embeddings, gt_data, emb_name)
            results.append(result)
            print(f"  ✓ {emb_name}: Top-5 = {result['metrics']['top_5']:.1f}%")

        all_results[gt_name] = results
        print_comparison_table(results, gt_name)

    # 결과 저장
    output = {
        "metadata": {
            "description": "8B vs 2B 임베딩 성능 비교",
            "created_at": datetime.now().isoformat(),
            "note": "8B = Qwen3-Embedding-8B (텍스트 전용), 2B = Qwen3-VL-Embedding-2B"
        },
        "results": {
            gt_name: {r['name']: r for r in results}
            for gt_name, results in all_results.items()
        }
    }

    output_path = RESULTS_DIR / "8b_vs_2b_comparison.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")

    # 결론 출력
    print("\n" + "="*80)
    print("  결론")
    print("="*80)

    for gt_name, results in all_results.items():
        best = max(results, key=lambda x: x['metrics']['top_5'])
        r8b = next((r for r in results if "8B" in r['name']), None)

        print(f"\n[{gt_name}]")
        print(f"  🏆 최고 성능: {best['name']} (Top-5: {best['metrics']['top_5']:.1f}%)")
        if r8b:
            diff = best['metrics']['top_5'] - r8b['metrics']['top_5']
            print(f"  📊 8B vs 최고: {r8b['metrics']['top_5']:.1f}% vs {best['metrics']['top_5']:.1f}% (차이: {diff:+.1f}%p)")

    print("\n" + "="*80)
    print("  📝 비교 대상:")
    print("     - 2B: Qwen3-VL-Embedding-2B (멀티모달, 2048 dim)")
    print("     - 8B VL: Qwen3-VL-Embedding-8B (멀티모달, 4096 dim)")
    print("="*80)


if __name__ == "__main__":
    main()
