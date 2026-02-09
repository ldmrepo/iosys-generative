#!/usr/bin/env python3
"""
Phase 1 & Phase 2 Implementation

Phase 1:
- MAP (Mean Average Precision) 지표 추가
- 수동 검증용 샘플 50개 추출

Phase 2:
- BM25 + Dense Hybrid Search 구현
- 평가 및 결과 비교
"""

import json
import re
import math
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import psycopg2


POC_DIR = Path(__file__).parent.parent
RESULTS_DIR = POC_DIR / "results"
DATA_DIR = POC_DIR / "data"

DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "poc_itembank",
    "user": "poc_user",
    "password": "poc_password",
}


class BM25:
    """BM25 검색 알고리즘 구현"""
    
    def __init__(self, k1=1.5, b=0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs = {}
        self.idf = {}
        self.doc_len = {}
        self.avgdl = 0
        self.docs = {}
        self.N = 0
        
    def tokenize(self, text):
        text = re.sub(r'[^\w\s가-힣]', ' ', text.lower())
        tokens = text.split()
        return [t for t in tokens if len(t) > 1]
    
    def fit(self, documents):
        self.N = len(documents)
        self.docs = documents
        
        total_len = 0
        df = defaultdict(int)
        
        for doc_id, text in documents.items():
            tokens = self.tokenize(text)
            self.doc_len[doc_id] = len(tokens)
            total_len += len(tokens)
            
            unique_tokens = set(tokens)
            for token in unique_tokens:
                df[token] += 1
        
        self.avgdl = total_len / self.N if self.N > 0 else 0
        
        for token, freq in df.items():
            self.idf[token] = math.log((self.N - freq + 0.5) / (freq + 0.5) + 1)
    
    def get_scores(self, query, exclude_id=None):
        query_tokens = self.tokenize(query)
        scores = {}
        
        for doc_id, text in self.docs.items():
            if doc_id == exclude_id:
                continue
                
            doc_tokens = self.tokenize(text)
            doc_len = self.doc_len[doc_id]
            
            score = 0.0
            token_freq = defaultdict(int)
            for t in doc_tokens:
                token_freq[t] += 1
            
            for token in query_tokens:
                if token not in self.idf:
                    continue
                    
                tf = token_freq.get(token, 0)
                idf = self.idf[token]
                
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += idf * numerator / denominator
            
            scores[doc_id] = score
        
        return scores


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def load_data():
    with open(DATA_DIR / "test_items.json") as f:
        items_data = json.load(f)
    
    with open(DATA_DIR / "ground_truth.json") as f:
        tfidf_gt = json.load(f)
    
    with open(DATA_DIR / "ground_truth_llm.json") as f:
        llm_gt = json.load(f)
    
    with open(DATA_DIR / "ground_truth_hybrid.json") as f:
        hybrid_gt = json.load(f)
    
    with open(RESULTS_DIR / "qwen_embeddings.json") as f:
        embeddings_data = json.load(f)
    
    return items_data, tfidf_gt, llm_gt, hybrid_gt, embeddings_data


def compute_similarity_matrix(embeddings_data):
    embeddings = embeddings_data["embeddings"]
    item_ids = list(embeddings.keys())
    
    emb_matrix = np.array([embeddings[item_id] for item_id in item_ids])
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    emb_matrix_normalized = emb_matrix / norms
    
    similarity_matrix = emb_matrix_normalized @ emb_matrix_normalized.T
    
    return item_ids, similarity_matrix


def get_dense_rankings(item_ids, similarity_matrix, query_id, top_k=20):
    query_idx = item_ids.index(query_id)
    similarities = similarity_matrix[query_idx].copy()
    similarities[query_idx] = -np.inf
    
    top_indices = np.argsort(-similarities)[:top_k]
    return [(item_ids[idx], float(similarities[idx])) for idx in top_indices]


def average_precision(predictions, ground_truth):
    """AP 계산"""
    pred_ids = [p[0] for p in predictions]
    relevant = set(ground_truth.keys())
    
    if not relevant:
        return 0.0
    
    hits = 0
    sum_precision = 0.0
    
    for i, pred_id in enumerate(pred_ids):
        if pred_id in relevant:
            hits += 1
            precision_at_i = hits / (i + 1)
            sum_precision += precision_at_i
    
    return sum_precision / len(relevant)


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


def evaluate_search(predictions_func, gt_data, description):
    """범용 검색 평가 함수"""
    metrics = {
        'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [], 'top_20': [],
        'mrr': [], 'map': [], 'ndcg_5': [], 'ndcg_10': []
    }
    
    by_category = defaultdict(lambda: defaultdict(list))
    
    for gt_item in gt_data["ground_truth"]:
        query_id = gt_item["query_id"]
        category = gt_item.get("query_category", "unknown")
        relevant = {item["id"]: item.get("relevance", 1) for item in gt_item["relevant_items"]}
        
        if not relevant:
            continue
        
        predictions = predictions_func(query_id)
        
        metrics['top_1'].append(top_k_recall(predictions, relevant, 1))
        metrics['top_3'].append(top_k_recall(predictions, relevant, 3))
        metrics['top_5'].append(top_k_recall(predictions, relevant, 5))
        metrics['top_10'].append(top_k_recall(predictions, relevant, 10))
        metrics['top_20'].append(top_k_recall(predictions, relevant, 20))
        metrics['mrr'].append(mrr(predictions, relevant))
        metrics['map'].append(average_precision(predictions, relevant))
        metrics['ndcg_5'].append(ndcg_at_k(predictions, relevant, 5))
        metrics['ndcg_10'].append(ndcg_at_k(predictions, relevant, 10))
        
        by_category[category]['top_5'].append(top_k_recall(predictions, relevant, 5))
        by_category[category]['top_10'].append(top_k_recall(predictions, relevant, 10))
        by_category[category]['mrr'].append(mrr(predictions, relevant))
        by_category[category]['map'].append(average_precision(predictions, relevant))
    
    return {
        'description': description,
        'total_queries': len(metrics['top_1']),
        'metrics': {k: float(np.mean(v)) for k, v in metrics.items()},
        'by_category': {
            cat: {k: float(np.mean(v)) for k, v in cat_metrics.items()}
            for cat, cat_metrics in by_category.items()
        }
    }


def hybrid_search(bm25, item_ids, similarity_matrix, query_id, query_text, 
                  alpha=0.5, top_k=20):
    query_idx = item_ids.index(query_id)
    similarities = similarity_matrix[query_idx].copy()
    
    dense_scores = {}
    for i, item_id in enumerate(item_ids):
        if item_id != query_id:
            dense_scores[item_id] = float(similarities[i])
    
    bm25_scores = bm25.get_scores(query_text, exclude_id=query_id)
    
    dense_vals = list(dense_scores.values())
    bm25_vals = [v for v in bm25_scores.values() if v > 0]
    
    dense_max = max(dense_vals) if dense_vals else 1
    dense_min = min(dense_vals) if dense_vals else 0
    bm25_max = max(bm25_vals) if bm25_vals else 1
    bm25_min = 0
    
    all_ids = set(dense_scores.keys())
    hybrid_scores = {}
    
    for item_id in all_ids:
        dense_norm = (dense_scores[item_id] - dense_min) / (dense_max - dense_min) if dense_max > dense_min else 0.5
        bm25_val = bm25_scores.get(item_id, 0)
        bm25_norm = bm25_val / bm25_max if bm25_max > 0 else 0
        
        hybrid_scores[item_id] = alpha * dense_norm + (1 - alpha) * bm25_norm
    
    sorted_results = sorted(hybrid_scores.items(), key=lambda x: -x[1])[:top_k]
    return sorted_results


def extract_manual_verification_samples(items_data, llm_gt, embeddings_data, n_samples=50):
    """수동 검증용 샘플 추출"""
    print("\n" + "="*80)
    print("수동 검증용 샘플 추출")
    print("="*80)
    
    item_ids, similarity_matrix = compute_similarity_matrix(embeddings_data)
    items_dict = {item["id"]: item for item in items_data["items"]}
    llm_gt_dict = {item["query_id"]: item for item in llm_gt["ground_truth"]}
    
    samples = []
    query_ids = list(llm_gt_dict.keys())[:n_samples]
    
    for query_id in query_ids:
        gt_item = llm_gt_dict[query_id]
        query_item = items_dict.get(query_id, {})
        
        query_content = query_item.get("content", {}).get("question", "")
        
        dense_results = get_dense_rankings(item_ids, similarity_matrix, query_id, top_k=10)
        
        sample = {
            "query_id": query_id,
            "query_content": query_content[:200] + "..." if len(query_content) > 200 else query_content,
            "category": gt_item.get("query_category", "unknown"),
            "llm_gt_items": [
                {
                    "id": item["id"],
                    "relevance": item.get("relevance", 0),
                    "reasoning": item.get("reasoning", "")[:100]
                }
                for item in gt_item["relevant_items"]
            ],
            "embedding_top10": [
                {
                    "rank": i + 1,
                    "id": item_id,
                    "similarity": round(score, 4),
                    "in_llm_gt": item_id in {it["id"] for it in gt_item["relevant_items"]},
                    "content_preview": items_dict.get(item_id, {}).get("content", {}).get("question", "")[:100]
                }
                for i, (item_id, score) in enumerate(dense_results)
            ]
        }
        samples.append(sample)
    
    output = {
        "metadata": {
            "total_samples": len(samples),
            "purpose": "수동 검증용 - LLM GT 품질 확인",
            "created_at": datetime.now().isoformat()
        },
        "verification_guide": {
            "task": "각 쿼리에 대해 embedding_top10의 항목들이 실제로 유사한 문항인지 확인",
            "check_points": [
                "LLM GT 항목이 실제로 유사한 문항인가?",
                "Embedding Top-10 중 LLM GT에 없지만 유사한 항목이 있는가?",
                "False Positive/Negative 비율은 적절한가?"
            ]
        },
        "samples": samples
    }
    
    output_path = DATA_DIR / "manual_verification_samples.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"  추출된 샘플: {len(samples)}개")
    print(f"  저장 위치: {output_path}")
    
    return output


def run_phase1(items_data, tfidf_gt, llm_gt, hybrid_gt, embeddings_data):
    """Phase 1: MAP 지표 추가 + 수동 검증 샘플"""
    print("\n" + "="*80)
    print("Phase 1: MAP 지표 추가 측정")
    print("="*80)
    
    item_ids, similarity_matrix = compute_similarity_matrix(embeddings_data)
    
    def dense_predictions(query_id):
        return get_dense_rankings(item_ids, similarity_matrix, query_id, top_k=20)
    
    results = {}
    for gt_data, gt_name in [(tfidf_gt, "TF-IDF GT"), (llm_gt, "LLM GT"), (hybrid_gt, "Hybrid GT")]:
        result = evaluate_search(dense_predictions, gt_data, f"Dense Search with {gt_name}")
        results[gt_name] = result
    
    print("\n" + "-"*80)
    print(f"{'GT Type':<15} | {'Top-5':>8} | {'Top-10':>8} | {'MRR':>8} | {'MAP':>8} | {'NDCG-10':>8}")
    print("-"*80)
    
    for gt_name, result in results.items():
        m = result['metrics']
        print(f"{gt_name:<15} | {m['top_5']:>7.1%} | {m['top_10']:>7.1%} | {m['mrr']:>7.1%} | {m['map']:>7.1%} | {m['ndcg_10']:>7.1%}")
    
    extract_manual_verification_samples(items_data, llm_gt, embeddings_data, n_samples=50)
    
    return results


def run_phase2(items_data, tfidf_gt, llm_gt, hybrid_gt, embeddings_data):
    """Phase 2: BM25 + Dense Hybrid Search"""
    print("\n" + "="*80)
    print("Phase 2: BM25 + Dense Hybrid Search")
    print("="*80)
    
    items_dict = {item["id"]: item for item in items_data["items"]}
    documents = {}
    for item_id, item in items_dict.items():
        content = item.get("content", {})
        text = content.get("question", "") + " " + content.get("explanation", "")
        documents[item_id] = text
    
    print("\nBM25 인덱스 구축 중...")
    bm25 = BM25(k1=1.5, b=0.75)
    bm25.fit(documents)
    print(f"  문서 수: {bm25.N}")
    print(f"  평균 문서 길이: {bm25.avgdl:.1f} tokens")
    print(f"  고유 토큰 수: {len(bm25.idf)}")
    
    item_ids, similarity_matrix = compute_similarity_matrix(embeddings_data)
    
    results_by_alpha = {}
    
    for alpha in [1.0, 0.7, 0.5, 0.3, 0.0]:
        alpha_name = f"alpha={alpha}"
        if alpha == 1.0:
            alpha_name = "Dense Only (α=1.0)"
        elif alpha == 0.0:
            alpha_name = "BM25 Only (α=0.0)"
        
        def hybrid_predictions(query_id, _alpha=alpha):
            query_text = documents.get(query_id, "")
            return hybrid_search(bm25, item_ids, similarity_matrix, query_id, query_text, 
                                alpha=_alpha, top_k=20)
        
        result = evaluate_search(hybrid_predictions, hybrid_gt, f"Hybrid Search {alpha_name}")
        results_by_alpha[alpha] = result
    
    print("\n" + "-"*80)
    print("Hybrid Search 결과 (Hybrid GT 기준)")
    print("-"*80)
    print(f"{'Alpha':<25} | {'Top-5':>8} | {'Top-10':>8} | {'MRR':>8} | {'MAP':>8}")
    print("-"*80)
    
    for alpha, result in results_by_alpha.items():
        m = result['metrics']
        desc = result['description'].replace("Hybrid Search ", "")
        print(f"{desc:<25} | {m['top_5']:>7.1%} | {m['top_10']:>7.1%} | {m['mrr']:>7.1%} | {m['map']:>7.1%}")
    
    best_alpha = max(results_by_alpha.keys(), key=lambda a: results_by_alpha[a]['metrics']['top_5'])
    print(f"\n최적 alpha 값: {best_alpha} (Top-5 Recall 기준)")
    
    return results_by_alpha, best_alpha


def main():
    print("="*80)
    print("Phase 1 & Phase 2 Implementation")
    print("="*80)
    
    print("\n데이터 로드 중...")
    items_data, tfidf_gt, llm_gt, hybrid_gt, embeddings_data = load_data()
    print(f"  테스트 문항: {len(items_data['items'])}개")
    print(f"  TF-IDF GT: {len(tfidf_gt['ground_truth'])} 쿼리")
    print(f"  LLM GT: {len(llm_gt['ground_truth'])} 쿼리")
    print(f"  Hybrid GT: {len(hybrid_gt['ground_truth'])} 쿼리")
    
    phase1_results = run_phase1(items_data, tfidf_gt, llm_gt, hybrid_gt, embeddings_data)
    
    phase2_results, best_alpha = run_phase2(items_data, tfidf_gt, llm_gt, hybrid_gt, embeddings_data)
    
    print("\n" + "="*80)
    print("최종 결과 요약")
    print("="*80)
    
    print("\n[Phase 1] MAP 지표 결과:")
    for gt_name, result in phase1_results.items():
        print(f"  {gt_name}: MAP = {result['metrics']['map']:.1%}")
    
    print(f"\n[Phase 2] Hybrid Search 최적 결과 (alpha={best_alpha}):")
    best_result = phase2_results[best_alpha]
    m = best_result['metrics']
    print(f"  Top-5 Recall: {m['top_5']:.1%}")
    print(f"  Top-10 Recall: {m['top_10']:.1%}")
    print(f"  MAP: {m['map']:.1%}")
    
    dense_only = phase2_results[1.0]['metrics']
    print(f"\n[비교] Dense Only vs Hybrid (alpha={best_alpha}):")
    print(f"  Top-5 Recall: {dense_only['top_5']:.1%} → {m['top_5']:.1%} ({m['top_5']-dense_only['top_5']:+.1%})")
    print(f"  Top-10 Recall: {dense_only['top_10']:.1%} → {m['top_10']:.1%} ({m['top_10']-dense_only['top_10']:+.1%})")
    print(f"  MAP: {dense_only['map']:.1%} → {m['map']:.1%} ({m['map']-dense_only['map']:+.1%})")
    
    output = {
        "phase1": {
            "description": "MAP 지표 추가 및 수동 검증 샘플 추출",
            "results": phase1_results
        },
        "phase2": {
            "description": "BM25 + Dense Hybrid Search",
            "best_alpha": best_alpha,
            "results_by_alpha": {str(k): v for k, v in phase2_results.items()}
        },
        "created_at": datetime.now().isoformat()
    }
    
    output_path = RESULTS_DIR / "phase1_phase2_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")
    
    print("\n" + "="*80)
    print("완료!")
    print("="*80)


if __name__ == "__main__":
    main()
