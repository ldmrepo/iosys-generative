#!/usr/bin/env python3
import json
import numpy as np
import psycopg2
from pathlib import Path
from collections import defaultdict

POC_DIR = Path(__file__).parent.parent
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "poc_itembank",
    "user": "poc_user",
    "password": "poc_password",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def load_ground_truth(gt_file: Path) -> dict:
    with open(gt_file, 'r') as f:
        data = json.load(f)
    
    gt_dict = {}
    for gt in data['ground_truth']:
        query_id = gt['query_id']
        gt_dict[query_id] = {
            'category': gt['query_category'],
            'relevant': {r['id']: r['relevance'] for r in gt['relevant_items']}
        }
    return gt_dict, data.get('metadata', {})

def search_similar(conn, table_name, query_id, top_k=20):
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
    pred_ids = [p[0] for p in predictions[:k]]
    hits = len(set(pred_ids) & set(ground_truth.keys()))
    return hits / len(ground_truth) if ground_truth else 0

def mrr(predictions, ground_truth):
    for i, (pred_id, _) in enumerate(predictions):
        if pred_id in ground_truth:
            return 1.0 / (i + 1)
    return 0.0

def ndcg_at_k(predictions, ground_truth, k):
    dcg = 0.0
    for i, (pred_id, _) in enumerate(predictions[:k]):
        if pred_id in ground_truth:
            relevance = ground_truth[pred_id]
            dcg += relevance / np.log2(i + 2)
    
    ideal_relevances = sorted(ground_truth.values(), reverse=True)[:k]
    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevances))
    
    return dcg / idcg if idcg > 0 else 0

def evaluate_with_gt(conn, table_name, ground_truth):
    metrics = {
        'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [], 'top_20': [],
        'mrr': [], 'ndcg_5': [], 'ndcg_10': []
    }
    by_category = defaultdict(lambda: defaultdict(list))
    
    for query_id, gt_info in ground_truth.items():
        relevant = gt_info['relevant']
        category = gt_info['category']
        
        if not relevant:
            continue
        
        results = search_similar(conn, table_name, query_id, top_k=20)
        if not results:
            continue
        
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
    print("=" * 70)
    print("Ground Truth Comparison: TF-IDF vs LLM")
    print("=" * 70)
    
    tfidf_gt_file = DATA_DIR / "ground_truth.json"
    llm_gt_file = DATA_DIR / "ground_truth_llm.json"
    
    print("\n[1/3] Loading Ground Truth files...")
    tfidf_gt, tfidf_meta = load_ground_truth(tfidf_gt_file)
    llm_gt, llm_meta = load_ground_truth(llm_gt_file)
    
    print(f"      TF-IDF GT: {len(tfidf_gt)} queries, {tfidf_meta.get('total_pairs', 'N/A')} pairs")
    print(f"      LLM GT: {len(llm_gt)} queries, {llm_meta.get('total_pairs', 'N/A')} pairs")
    
    conn = get_connection()
    
    print("\n[2/3] Evaluating Qwen3-VL embeddings with both GTs...")
    
    tfidf_results = evaluate_with_gt(conn, "qwen_embeddings", tfidf_gt)
    llm_results = evaluate_with_gt(conn, "qwen_embeddings", llm_gt)
    
    conn.close()
    
    print("\n[3/3] Results Comparison")
    print("=" * 70)
    
    print(f"\n{'Metric':<15} {'TF-IDF GT':<15} {'LLM GT':<15} {'Change':<15}")
    print("-" * 60)
    
    for metric in ['top_1', 'top_3', 'top_5', 'top_10', 'mrr', 'ndcg_10']:
        tfidf_val = tfidf_results['metrics'][metric]
        llm_val = llm_results['metrics'][metric]
        change = llm_val - tfidf_val
        sign = "+" if change >= 0 else ""
        
        label = metric.replace('_', '-').upper()
        print(f"{label:<15} {tfidf_val:.4f}          {llm_val:.4f}          {sign}{change:.4f}")
    
    print("\n" + "=" * 70)
    print("Category-wise Top-5 Recall")
    print("=" * 70)
    
    categories = set(tfidf_results['by_category'].keys()) | set(llm_results['by_category'].keys())
    
    print(f"\n{'Category':<15} {'TF-IDF GT':<15} {'LLM GT':<15} {'Change':<15}")
    print("-" * 60)
    
    for cat in sorted(categories):
        tfidf_val = tfidf_results['by_category'].get(cat, {}).get('top_5', 0)
        llm_val = llm_results['by_category'].get(cat, {}).get('top_5', 0)
        change = llm_val - tfidf_val
        sign = "+" if change >= 0 else ""
        print(f"{cat:<15} {tfidf_val:.4f}          {llm_val:.4f}          {sign}{change:.4f}")
    
    output = {
        "tfidf_gt": {
            "metadata": tfidf_meta,
            "results": tfidf_results
        },
        "llm_gt": {
            "metadata": llm_meta,
            "results": llm_results
        },
        "improvement": {
            metric: llm_results['metrics'][metric] - tfidf_results['metrics'][metric]
            for metric in tfidf_results['metrics']
        }
    }
    
    output_file = RESULTS_DIR / "gt_comparison.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    top5_change = output["improvement"]["top_5"] * 100
    mrr_change = output["improvement"]["mrr"] * 100
    
    print(f"\nTop-5 Recall: {tfidf_results['metrics']['top_5']*100:.1f}% -> {llm_results['metrics']['top_5']*100:.1f}% ({'+' if top5_change >= 0 else ''}{top5_change:.1f}%p)")
    print(f"MRR:          {tfidf_results['metrics']['mrr']*100:.1f}% -> {llm_results['metrics']['mrr']*100:.1f}% ({'+' if mrr_change >= 0 else ''}{mrr_change:.1f}%p)")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
