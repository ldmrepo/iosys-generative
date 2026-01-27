#!/usr/bin/env python3
"""
Task #13-16: 검색 평가 스크립트
각 모델별 검색 정확도 평가 (Top-K Recall, MRR, NDCG)
"""
import json
import argparse
import numpy as np
import psycopg2
from pathlib import Path
from collections import defaultdict

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
RESULTS_DIR = POC_DIR / "results"
DATA_DIR = POC_DIR / "data"

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

def search_similar(conn, table_name, query_id, top_k=20):
    """pgvector를 사용한 유사도 검색"""
    with conn.cursor() as cur:
        # Get query embedding
        cur.execute(f"SELECT embedding FROM {table_name} WHERE id = %s", (query_id,))
        result = cur.fetchone()
        if not result:
            return []

        # Search similar items (cosine distance)
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

def evaluate_model(conn, table_name, ground_truth, model_name):
    """단일 모델 평가"""
    print(f"\n{'='*60}")
    print(f"Evaluating: {model_name}")
    print(f"Table: {table_name}")
    print(f"{'='*60}")

    metrics = {
        'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [], 'top_20': [],
        'mrr': [], 'ndcg_5': [], 'ndcg_10': []
    }

    by_category = defaultdict(lambda: defaultdict(list))

    for query_id, gt_info in ground_truth.items():
        relevant = gt_info['relevant']
        category = gt_info['category']

        # Search
        results = search_similar(conn, table_name, query_id, top_k=20)

        if not results:
            continue

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

        # By category
        by_category[category]['top_5'].append(r5)
        by_category[category]['top_10'].append(r10)
        by_category[category]['mrr'].append(m)

    # Average metrics
    results = {
        'model': model_name,
        'table': table_name,
        'total_queries': len(metrics['top_1']),
        'metrics': {k: float(np.mean(v)) for k, v in metrics.items()},
        'by_category': {
            cat: {k: float(np.mean(v)) for k, v in cat_metrics.items()}
            for cat, cat_metrics in by_category.items()
        }
    }

    # Print results
    print(f"\nOverall Results (n={results['total_queries']}):")
    print(f"  Top-1 Recall:  {results['metrics']['top_1']:.4f}")
    print(f"  Top-3 Recall:  {results['metrics']['top_3']:.4f}")
    print(f"  Top-5 Recall:  {results['metrics']['top_5']:.4f} {'✓' if results['metrics']['top_5'] >= 0.8 else '✗'} (target: ≥0.80)")
    print(f"  Top-10 Recall: {results['metrics']['top_10']:.4f} {'✓' if results['metrics']['top_10'] >= 0.9 else '✗'} (target: ≥0.90)")
    print(f"  Top-20 Recall: {results['metrics']['top_20']:.4f}")
    print(f"  MRR:           {results['metrics']['mrr']:.4f} {'✓' if results['metrics']['mrr'] >= 0.65 else '✗'} (target: ≥0.65)")
    print(f"  NDCG@5:        {results['metrics']['ndcg_5']:.4f}")
    print(f"  NDCG@10:       {results['metrics']['ndcg_10']:.4f}")

    print(f"\nBy Category:")
    for cat, cat_metrics in results['by_category'].items():
        print(f"  {cat}:")
        print(f"    Top-5: {cat_metrics['top_5']:.4f}, Top-10: {cat_metrics['top_10']:.4f}, MRR: {cat_metrics['mrr']:.4f}")

    return results

def main():
    parser = argparse.ArgumentParser(description='Search evaluation')
    parser.add_argument('--model', choices=['qwen', 'kure', 'siglip', 'combined', 'all'],
                        default='all', help='Model to evaluate')
    args = parser.parse_args()

    print("=" * 60)
    print("검색 평가")
    print("=" * 60)

    # Load ground truth
    print("\nLoading ground truth...")
    ground_truth = load_ground_truth()
    print(f"  Queries: {len(ground_truth)}")

    conn = get_connection()

    models = {
        'qwen': ('qwen_embeddings', 'Qwen3-VL-Embedding-2B'),
        'kure': ('kure_embeddings', 'KURE-v1'),
        'siglip': ('siglip_embeddings', 'SigLIP'),
        'combined': ('combined_embeddings', 'KURE+SigLIP'),
    }

    if args.model == 'all':
        selected = models.keys()
    else:
        selected = [args.model]

    all_results = []

    for model_key in selected:
        table_name, model_name = models[model_key]
        result = evaluate_model(conn, table_name, ground_truth, model_name)
        all_results.append(result)

    conn.close()

    # Save results
    output_file = RESULTS_DIR / "search_evaluation.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {output_file}")

    # Comparison summary
    if len(all_results) > 1:
        print("\n" + "=" * 60)
        print("모델 비교 요약")
        print("=" * 60)
        print(f"\n{'Model':<25} {'Top-5':<10} {'Top-10':<10} {'MRR':<10}")
        print("-" * 55)
        for r in all_results:
            m = r['metrics']
            print(f"{r['model']:<25} {m['top_5']:.4f}     {m['top_10']:.4f}     {m['mrr']:.4f}")

    print("\n" + "=" * 60)
    print("평가 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
