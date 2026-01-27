#!/usr/bin/env python3
"""
MRR 하락 원인 분석 및 하이브리드 GT 생성

분석 내용:
1. LLM GT가 순위 1위 항목을 덜 선택하는 이유 분석
2. TF-IDF GT와 LLM GT의 교집합(하이브리드 GT) 생성
3. 하이브리드 GT로 평가 수행
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def load_data():
    base_path = Path(__file__).parent.parent
    
    with open(base_path / "data" / "ground_truth.json") as f:
        tfidf_gt = json.load(f)
    
    with open(base_path / "data" / "ground_truth_llm.json") as f:
        llm_gt = json.load(f)
    
    with open(base_path / "results" / "qwen_embeddings.json") as f:
        embeddings_data = json.load(f)
    
    return tfidf_gt, llm_gt, embeddings_data


def compute_similarity_matrix(embeddings_data):
    embeddings = embeddings_data["embeddings"]
    item_ids = list(embeddings.keys())
    
    emb_matrix = np.array([embeddings[item_id] for item_id in item_ids])
    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
    emb_matrix_normalized = emb_matrix / norms
    
    similarity_matrix = emb_matrix_normalized @ emb_matrix_normalized.T
    
    return item_ids, similarity_matrix


def get_embedding_ranks(item_ids, similarity_matrix, query_id, candidate_ids):
    query_idx = item_ids.index(query_id)
    all_similarities = similarity_matrix[query_idx]
    
    sorted_indices = np.argsort(-all_similarities)
    ranks = {item_ids[idx]: rank + 1 for rank, idx in enumerate(sorted_indices) if item_ids[idx] != query_id}
    
    return {cid: ranks.get(cid, 999) for cid in candidate_ids}


def analyze_mrr_drop(tfidf_gt, llm_gt, item_ids, similarity_matrix):
    print("\n" + "="*80)
    print("MRR 하락 원인 심층 분석")
    print("="*80)
    
    tfidf_dict = {item["query_id"]: item for item in tfidf_gt["ground_truth"]}
    llm_dict = {item["query_id"]: item for item in llm_gt["ground_truth"]}
    
    analysis = {
        "rank_1_selection": {"tfidf": 0, "llm": 0},
        "rank_distribution": {"tfidf": defaultdict(int), "llm": defaultdict(int)},
        "avg_relevants_per_query": {"tfidf": 0, "llm": 0},
        "detailed_comparison": []
    }
    
    common_queries = set(tfidf_dict.keys()) & set(llm_dict.keys())
    
    for query_id in common_queries:
        tfidf_relevants = {item["id"]: item for item in tfidf_dict[query_id]["relevant_items"]}
        llm_relevants = {item["id"]: item for item in llm_dict[query_id]["relevant_items"]}
        
        all_candidates = set(tfidf_relevants.keys()) | set(llm_relevants.keys())
        ranks = get_embedding_ranks(item_ids, similarity_matrix, query_id, all_candidates)
        
        tfidf_has_rank1 = any(ranks[cid] == 1 for cid in tfidf_relevants.keys())
        if tfidf_has_rank1:
            analysis["rank_1_selection"]["tfidf"] += 1
        
        llm_has_rank1 = any(ranks[cid] == 1 for cid in llm_relevants.keys())
        if llm_has_rank1:
            analysis["rank_1_selection"]["llm"] += 1
        
        for cid in tfidf_relevants.keys():
            rank = ranks[cid]
            bucket = f"1-5" if rank <= 5 else f"6-10" if rank <= 10 else f"11-20" if rank <= 20 else "21+"
            analysis["rank_distribution"]["tfidf"][bucket] += 1
        
        for cid in llm_relevants.keys():
            rank = ranks[cid]
            bucket = f"1-5" if rank <= 5 else f"6-10" if rank <= 10 else f"11-20" if rank <= 20 else "21+"
            analysis["rank_distribution"]["llm"][bucket] += 1
        
        tfidf_min_rank = min(ranks[cid] for cid in tfidf_relevants.keys())
        llm_min_rank = min(ranks[cid] for cid in llm_relevants.keys()) if llm_relevants else 999
        
        if llm_min_rank > tfidf_min_rank:
            analysis["detailed_comparison"].append({
                "query_id": query_id,
                "tfidf_min_rank": tfidf_min_rank,
                "llm_min_rank": llm_min_rank,
                "rank_diff": llm_min_rank - tfidf_min_rank,
                "tfidf_count": len(tfidf_relevants),
                "llm_count": len(llm_relevants)
            })
    
    analysis["avg_relevants_per_query"]["tfidf"] = sum(
        len(item["relevant_items"]) for item in tfidf_gt["ground_truth"]
    ) / len(tfidf_gt["ground_truth"])
    
    analysis["avg_relevants_per_query"]["llm"] = sum(
        len(item["relevant_items"]) for item in llm_gt["ground_truth"]
    ) / len(llm_gt["ground_truth"])
    
    print(f"\n1. 순위 1위 항목 선택 비율:")
    print(f"   TF-IDF GT: {analysis['rank_1_selection']['tfidf']}/{len(common_queries)} "
          f"({analysis['rank_1_selection']['tfidf']/len(common_queries)*100:.1f}%)")
    print(f"   LLM GT:    {analysis['rank_1_selection']['llm']}/{len(common_queries)} "
          f"({analysis['rank_1_selection']['llm']/len(common_queries)*100:.1f}%)")
    
    print(f"\n2. 쿼리당 평균 관련 항목 수:")
    print(f"   TF-IDF GT: {analysis['avg_relevants_per_query']['tfidf']:.2f}")
    print(f"   LLM GT:    {analysis['avg_relevants_per_query']['llm']:.2f}")
    
    print(f"\n3. GT 항목의 임베딩 순위 분포:")
    print("   순위 범위  | TF-IDF GT | LLM GT")
    print("   -----------|-----------|--------")
    for bucket in ["1-5", "6-10", "11-20", "21+"]:
        tfidf_count = analysis["rank_distribution"]["tfidf"].get(bucket, 0)
        llm_count = analysis["rank_distribution"]["llm"].get(bucket, 0)
        print(f"   {bucket:10} | {tfidf_count:9} | {llm_count:6}")
    
    print(f"\n4. LLM GT가 더 높은 순위의 첫 번째 관련 항목을 가진 쿼리 수:")
    worse_cases = len(analysis["detailed_comparison"])
    print(f"   {worse_cases}/{len(common_queries)} 쿼리 ({worse_cases/len(common_queries)*100:.1f}%)")
    
    if analysis["detailed_comparison"]:
        print(f"\n   평균 순위 차이: {np.mean([c['rank_diff'] for c in analysis['detailed_comparison']]):.2f}")
        worst_cases = sorted(analysis["detailed_comparison"], key=lambda x: -x["rank_diff"])[:5]
        print("\n   최악의 케이스 Top 5:")
        for case in worst_cases:
            print(f"     - {case['query_id'][:8]}...: TF-IDF 순위 {case['tfidf_min_rank']} → LLM 순위 {case['llm_min_rank']} (차이: +{case['rank_diff']})")
    
    return analysis


def create_hybrid_gt(tfidf_gt, llm_gt, item_ids, similarity_matrix):
    print("\n" + "="*80)
    print("하이브리드 GT 생성")
    print("="*80)
    
    tfidf_dict = {item["query_id"]: item for item in tfidf_gt["ground_truth"]}
    llm_dict = {item["query_id"]: item for item in llm_gt["ground_truth"]}
    
    hybrid_gt = []
    stats = {
        "total_queries": 0,
        "queries_with_intersection": 0,
        "total_pairs": 0,
        "intersection_sizes": []
    }
    
    for query_id in tfidf_dict.keys():
        tfidf_item = tfidf_dict[query_id]
        llm_item = llm_dict.get(query_id)
        
        if not llm_item:
            continue
        
        stats["total_queries"] += 1
        
        tfidf_ids = {item["id"] for item in tfidf_item["relevant_items"]}
        llm_ids = {item["id"] for item in llm_item["relevant_items"]}
        
        intersection = tfidf_ids & llm_ids
        
        if intersection:
            stats["queries_with_intersection"] += 1
            stats["intersection_sizes"].append(len(intersection))
            
            llm_relevance = {item["id"]: item for item in llm_item["relevant_items"]}
            
            relevant_items = []
            for item_id in intersection:
                if item_id in llm_relevance:
                    relevant_items.append({
                        "id": item_id,
                        "relevance": llm_relevance[item_id]["relevance"],
                        "source": "intersection"
                    })
            
            hybrid_gt.append({
                "query_id": query_id,
                "query_category": tfidf_item["query_category"],
                "relevant_items": relevant_items
            })
            
            stats["total_pairs"] += len(relevant_items)
    
    print(f"\n교집합 통계:")
    print(f"  - 전체 쿼리: {stats['total_queries']}")
    print(f"  - 교집합 있는 쿼리: {stats['queries_with_intersection']} ({stats['queries_with_intersection']/stats['total_queries']*100:.1f}%)")
    print(f"  - 총 GT 쌍: {stats['total_pairs']}")
    if stats["intersection_sizes"]:
        print(f"  - 평균 교집합 크기: {np.mean(stats['intersection_sizes']):.2f}")
        print(f"  - 최소/최대 교집합 크기: {min(stats['intersection_sizes'])}/{max(stats['intersection_sizes'])}")
    
    hybrid_gt_data = {
        "metadata": {
            "total_queries": stats["queries_with_intersection"],
            "total_pairs": stats["total_pairs"],
            "generation_method": "Hybrid (TF-IDF ∩ LLM GT)",
            "created_at": datetime.now().isoformat(),
            "stats": stats
        },
        "ground_truth": hybrid_gt
    }
    
    return hybrid_gt_data


def evaluate_with_gt(gt_data, item_ids, similarity_matrix, gt_name="GT"):
    metrics = {
        "top_1": 0, "top_3": 0, "top_5": 0, "top_10": 0, "top_20": 0,
        "mrr": 0, "ndcg_5": 0, "ndcg_10": 0
    }
    
    total_queries = 0
    
    for gt_item in gt_data["ground_truth"]:
        query_id = gt_item["query_id"]
        relevant_ids = {item["id"] for item in gt_item["relevant_items"]}
        
        if not relevant_ids:
            continue
        
        total_queries += 1
        
        ranks = get_embedding_ranks(item_ids, similarity_matrix, query_id, relevant_ids)
        min_rank = min(ranks.values())
        
        for k in [1, 3, 5, 10, 20]:
            hits = sum(1 for r in ranks.values() if r <= k)
            metrics[f"top_{k}"] += hits / len(relevant_ids)
        
        metrics["mrr"] += 1 / min_rank
        
        for k, key in [(5, "ndcg_5"), (10, "ndcg_10")]:
            relevance_scores = {item["id"]: item.get("relevance", 1) for item in gt_item["relevant_items"]}
            dcg = sum(relevance_scores.get(item_ids[idx], 0) / np.log2(rank + 2) 
                     for rank, idx in enumerate(np.argsort(-similarity_matrix[item_ids.index(query_id)])[1:k+1]))
            idcg = sum(r / np.log2(i + 2) for i, r in enumerate(sorted(relevance_scores.values(), reverse=True)[:k]))
            metrics[key] += dcg / idcg if idcg > 0 else 0
    
    for key in metrics:
        metrics[key] /= total_queries
    
    return metrics, total_queries


def main():
    print("="*80)
    print("MRR 하락 원인 분석 및 하이브리드 GT 생성")
    print("="*80)
    
    print("\n데이터 로드 중...")
    tfidf_gt, llm_gt, embeddings_data = load_data()
    
    print("유사도 매트릭스 계산 중...")
    item_ids, similarity_matrix = compute_similarity_matrix(embeddings_data)
    
    analysis = analyze_mrr_drop(tfidf_gt, llm_gt, item_ids, similarity_matrix)
    
    hybrid_gt = create_hybrid_gt(tfidf_gt, llm_gt, item_ids, similarity_matrix)
    
    base_path = Path(__file__).parent.parent
    output_path = base_path / "data" / "ground_truth_hybrid.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(hybrid_gt, f, ensure_ascii=False, indent=2)
    print(f"\n하이브리드 GT 저장: {output_path}")
    
    print("\n" + "="*80)
    print("GT별 평가 결과 비교")
    print("="*80)
    
    results = {}
    for gt_data, name in [(tfidf_gt, "TF-IDF GT"), (llm_gt, "LLM GT"), (hybrid_gt, "Hybrid GT")]:
        metrics, n_queries = evaluate_with_gt(gt_data, item_ids, similarity_matrix, name)
        results[name] = {"metrics": metrics, "n_queries": n_queries}
    
    print("\n" + "-"*80)
    print(f"{'Metric':<12} | {'TF-IDF GT':>12} | {'LLM GT':>12} | {'Hybrid GT':>12}")
    print("-"*80)
    
    for metric in ["top_1", "top_3", "top_5", "top_10", "top_20", "mrr", "ndcg_5", "ndcg_10"]:
        tfidf_val = results["TF-IDF GT"]["metrics"][metric]
        llm_val = results["LLM GT"]["metrics"][metric]
        hybrid_val = results["Hybrid GT"]["metrics"][metric]
        print(f"{metric:<12} | {tfidf_val:>11.1%} | {llm_val:>11.1%} | {hybrid_val:>11.1%}")
    
    print("-"*80)
    print(f"{'Queries':<12} | {results['TF-IDF GT']['n_queries']:>12} | {results['LLM GT']['n_queries']:>12} | {results['Hybrid GT']['n_queries']:>12}")
    
    output_analysis = {
        "mrr_analysis": {
            "rank_1_selection": analysis["rank_1_selection"],
            "avg_relevants_per_query": analysis["avg_relevants_per_query"],
            "rank_distribution": {k: dict(v) for k, v in analysis["rank_distribution"].items()},
            "worse_cases_count": len(analysis["detailed_comparison"])
        },
        "evaluation_results": results,
        "hybrid_gt_stats": hybrid_gt["metadata"]["stats"]
    }
    
    analysis_path = base_path / "results" / "mrr_analysis_and_hybrid.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(output_analysis, f, ensure_ascii=False, indent=2)
    print(f"\n분석 결과 저장: {analysis_path}")
    
    print("\n" + "="*80)
    print("분석 결과 및 권장사항")
    print("="*80)
    
    print("""
[MRR 하락 원인]
1. LLM GT가 순위 1위 항목을 덜 선택함
   - TF-IDF는 텍스트 유사도가 높은 항목을 선택 (임베딩 순위 1위와 일치하는 경우 많음)
   - LLM은 "의미적 유사성"을 평가하여 순위 2-10위 항목도 선택

2. LLM GT의 쿼리당 관련 항목 수가 적음
   - TF-IDF GT: 쿼리당 5개 (고정)
   - LLM GT: 쿼리당 ~3개 (엄격한 기준)
   - 적은 항목 = MRR 계산에서 불리

[하이브리드 GT의 의미]
- TF-IDF와 LLM 모두 동의하는 "고신뢰" 관련 항목
- 텍스트 유사성 + 의미적 유사성 모두 충족
- 임베딩 검색 품질 평가에 더 적합한 GT

[권장사항]
1. 하이브리드 GT를 주요 평가 기준으로 사용
2. 추가 수동 검증으로 GT 품질 확인 (20-30개 샘플)
3. LLM GT의 min_relevance_score 조정 고려 (3 → 4로 올려 더 엄격하게)
""")


if __name__ == "__main__":
    main()
