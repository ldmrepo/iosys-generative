#!/usr/bin/env python3
"""
Qwen3-VL-Reranker 적용 검색 평가
Two-stage retrieval: Embedding (Top-20) -> Reranker (Top-10)
"""
import json
import sys
import torch
import numpy as np
import psycopg2
from pathlib import Path
from collections import defaultdict
from tqdm import tqdm

# Add reranker scripts to path
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
RERANKER_PATH = POC_DIR / "models/qwen3-vl-reranker-2b"
sys.path.insert(0, str(RERANKER_PATH / "scripts"))

from qwen3_vl_reranker import Qwen3VLReranker

# Paths
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"

# Database config
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "poc_itembank",
    "user": "poc_user",
    "password": "poc_password",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def load_ground_truth():
    """Ground truth 로드"""
    with open(DATA_DIR / "ground_truth.json", 'r') as f:
        data = json.load(f)

    gt_dict = {}
    for gt in data['ground_truth']:
        query_id = gt['query_id']
        gt_dict[query_id] = {
            'category': gt['query_category'],
            'relevant': {r['id']: r['relevance'] for r in gt['relevant_items']}
        }
    return gt_dict

def load_test_items():
    """테스트 문항 로드"""
    with open(DATA_DIR / "test_items.json", 'r') as f:
        data = json.load(f)

    items = {}
    for item in data['items']:
        items[item['id']] = {
            'question': item.get('content', {}).get('question', ''),
            'has_image': item.get('has_image', False),
            'image_path': item.get('image_path', None)
        }
    return items

def search_similar(conn, table_name, query_id, top_k=20):
    """pgvector를 사용한 유사도 검색"""
    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT id, 1 - (embedding <=> (SELECT embedding FROM {table_name} WHERE id = %s)) as similarity
            FROM {table_name}
            WHERE id != %s
            ORDER BY embedding <=> (SELECT embedding FROM {table_name} WHERE id = %s)
            LIMIT %s
        """, (query_id, query_id, query_id, top_k))
        return [(row[0], row[1]) for row in cur.fetchall()]

def top_k_recall(predictions, ground_truth, k):
    """Top-K Recall 계산"""
    pred_ids = [p[0] for p in predictions[:k]]
    hits = len(set(pred_ids) & set(ground_truth.keys()))
    return hits / len(ground_truth) if ground_truth else 0

def mrr(predictions, ground_truth):
    """Mean Reciprocal Rank 계산"""
    for i, (pred_id, _) in enumerate(predictions):
        if pred_id in ground_truth:
            return 1.0 / (i + 1)
    return 0.0

def ndcg_at_k(predictions, ground_truth, k):
    """NDCG@K 계산"""
    dcg = 0.0
    for i, (pred_id, _) in enumerate(predictions[:k]):
        if pred_id in ground_truth:
            relevance = ground_truth[pred_id]
            dcg += relevance / np.log2(i + 2)

    # Ideal DCG
    ideal_relevances = sorted(ground_truth.values(), reverse=True)[:k]
    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevances))

    return dcg / idcg if idcg > 0 else 0

def rerank_with_model(reranker, query_item, candidate_items, test_items):
    """Reranker로 후보 재정렬"""
    query_text = test_items[query_item]['question']

    documents = []
    for cand_id, _ in candidate_items:
        doc_text = test_items.get(cand_id, {}).get('question', '')
        documents.append({"text": doc_text})

    if not documents:
        return candidate_items

    inputs = {
        "instruction": "주어진 쿼리 문항과 유사한 수학 문항을 찾아주세요. 같은 개념이나 유형의 문항이 관련됩니다.",
        "query": {"text": query_text},
        "documents": documents
    }

    try:
        scores = reranker.process(inputs)

        # Combine with original candidates and rerank
        reranked = []
        for (cand_id, orig_score), rerank_score in zip(candidate_items, scores):
            reranked.append((cand_id, rerank_score))

        # Sort by reranker score (descending)
        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked
    except Exception as e:
        print(f"Reranking error: {e}")
        return candidate_items

def evaluate(conn, ground_truth, test_items, reranker=None, use_reranker=False):
    """평가 실행"""
    metrics = {
        'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [], 'top_20': [],
        'mrr': [], 'ndcg_5': [], 'ndcg_10': []
    }
    by_category = defaultdict(lambda: defaultdict(list))

    desc = "Evaluating with Reranker" if use_reranker else "Evaluating without Reranker"

    for query_id in tqdm(ground_truth.keys(), desc=desc):
        gt_info = ground_truth[query_id]
        relevant = gt_info['relevant']
        category = gt_info['category']

        # Stage 1: Embedding search (Top-20)
        candidates = search_similar(conn, "qwen_embeddings", query_id, top_k=20)

        if not candidates:
            continue

        # Stage 2: Reranking (optional)
        if use_reranker and reranker:
            results = rerank_with_model(reranker, query_id, candidates, test_items)
        else:
            results = candidates

        # Calculate metrics
        r1 = top_k_recall(results, relevant, 1)
        r3 = top_k_recall(results, relevant, 3)
        r5 = top_k_recall(results, relevant, 5)
        r10 = top_k_recall(results, relevant, 10)
        r20 = top_k_recall(results, relevant, 20)
        m = mrr(results, relevant)
        n5 = ndcg_at_k(results, relevant, 5)
        n10 = ndcg_at_k(results, relevant, 10)

        metrics['top_1'].append(r1)
        metrics['top_3'].append(r3)
        metrics['top_5'].append(r5)
        metrics['top_10'].append(r10)
        metrics['top_20'].append(r20)
        metrics['mrr'].append(m)
        metrics['ndcg_5'].append(n5)
        metrics['ndcg_10'].append(n10)

        by_category[category]['top_5'].append(r5)
        by_category[category]['top_10'].append(r10)
        by_category[category]['mrr'].append(m)

    return {
        'metrics': {k: float(np.mean(v)) for k, v in metrics.items()},
        'by_category': {
            cat: {k: float(np.mean(v)) for k, v in cat_metrics.items()}
            for cat, cat_metrics in by_category.items()
        },
        'total_queries': len(metrics['top_1'])
    }

def main():
    print("=" * 60)
    print("Qwen3-VL-Reranker 적용 검색 평가")
    print("=" * 60)

    # GPU info
    if torch.cuda.is_available():
        print(f"\nGPU: {torch.cuda.get_device_name(0)}")

    # Load data
    print("\n[1/4] 데이터 로드...")
    ground_truth = load_ground_truth()
    test_items = load_test_items()
    print(f"      Queries: {len(ground_truth)}, Items: {len(test_items)}")

    conn = get_connection()

    # Evaluate WITHOUT reranker (baseline)
    print("\n[2/4] Baseline 평가 (Embedding only)...")
    baseline_results = evaluate(conn, ground_truth, test_items, use_reranker=False)

    # Load reranker
    print("\n[3/4] Reranker 모델 로드...")
    reranker = Qwen3VLReranker(
        model_name_or_path=str(RERANKER_PATH),
        torch_dtype=torch.float16
    )
    print(f"      VRAM: {torch.cuda.memory_allocated()/1e9:.2f} GB")

    # Evaluate WITH reranker
    print("\n[4/4] Reranker 평가 (Embedding + Reranker)...")
    reranker_results = evaluate(conn, ground_truth, test_items, reranker=reranker, use_reranker=True)

    conn.close()

    # Print comparison
    print("\n" + "=" * 60)
    print("결과 비교")
    print("=" * 60)

    print(f"\n{'지표':<15} {'Baseline':<12} {'+ Reranker':<12} {'개선':<10}")
    print("-" * 50)

    for metric in ['top_1', 'top_3', 'top_5', 'top_10', 'mrr', 'ndcg_10']:
        base = baseline_results['metrics'][metric]
        rerank = reranker_results['metrics'][metric]
        diff = rerank - base
        sign = "+" if diff >= 0 else ""

        label = metric.replace('_', '-').upper()
        print(f"{label:<15} {base:.4f}       {rerank:.4f}       {sign}{diff:.4f}")

    # Category comparison
    print("\n카테고리별 Top-5 Recall:")
    print("-" * 50)
    for cat in baseline_results['by_category'].keys():
        base = baseline_results['by_category'][cat]['top_5']
        rerank = reranker_results['by_category'].get(cat, {}).get('top_5', 0)
        diff = rerank - base
        sign = "+" if diff >= 0 else ""
        print(f"  {cat:<12} {base:.4f} -> {rerank:.4f} ({sign}{diff:.4f})")

    # Save results
    output = {
        "baseline": baseline_results,
        "with_reranker": reranker_results,
        "improvement": {
            metric: reranker_results['metrics'][metric] - baseline_results['metrics'][metric]
            for metric in baseline_results['metrics']
        }
    }

    output_file = RESULTS_DIR / "reranker_evaluation.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    # Summary
    print("\n" + "=" * 60)
    print("요약")
    print("=" * 60)

    top5_improvement = output["improvement"]["top_5"] * 100
    top10_improvement = output["improvement"]["top_10"] * 100
    mrr_improvement = output["improvement"]["mrr"] * 100

    print(f"\nReranker 적용 효과:")
    print(f"  Top-5 Recall:  {baseline_results['metrics']['top_5']*100:.1f}% -> {reranker_results['metrics']['top_5']*100:.1f}% ({'+' if top5_improvement >= 0 else ''}{top5_improvement:.1f}%p)")
    print(f"  Top-10 Recall: {baseline_results['metrics']['top_10']*100:.1f}% -> {reranker_results['metrics']['top_10']*100:.1f}% ({'+' if top10_improvement >= 0 else ''}{top10_improvement:.1f}%p)")
    print(f"  MRR:           {baseline_results['metrics']['mrr']*100:.1f}% -> {reranker_results['metrics']['mrr']*100:.1f}% ({'+' if mrr_improvement >= 0 else ''}{mrr_improvement:.1f}%p)")

    print("\n" + "=" * 60)
    print("Reranker 평가 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
