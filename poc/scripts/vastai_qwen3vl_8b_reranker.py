#!/usr/bin/env python3
"""
Vast.ai용 Qwen3-VL-Reranker-8B 평가 스크립트

사용법:
1. 필요 파일 업로드:
   - test_items.json
   - qwen_vl_embeddings_8b.json (임베딩 생성 후)
   - ground_truth_image.json
   - ground_truth_hybrid.json
2. pip install torch transformers accelerate tqdm qwen-vl-utils
3. python vastai_qwen3vl_8b_reranker.py

출력: qwen_vl_reranker_8b_evaluation.json
"""

import json
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm
from datetime import datetime

# Configuration
MODEL_NAME = "Qwen/Qwen3-VL-Reranker-8B"
EMBEDDINGS_FILE = "qwen_vl_embeddings_8b.json"
DATA_FILE = "test_items.json"
IMAGE_GT_FILE = "ground_truth_image.json"
HYBRID_GT_FILE = "ground_truth_hybrid.json"
OUTPUT_FILE = "qwen_vl_reranker_8b_evaluation.json"
TOP_K_CANDIDATES = 50


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        reserved = torch.cuda.memory_reserved() / 1e9
        return f"Allocated: {allocated:.2f}GB, Reserved: {reserved:.2f}GB"
    return "N/A"


def load_reranker():
    """Qwen3-VL-Reranker-8B 모델 로드"""
    from transformers import AutoModelForSequenceClassification, AutoProcessor

    print(f"Loading Reranker: {MODEL_NAME}")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True
    )
    model.eval()

    print(f"Reranker loaded. GPU memory: {get_gpu_memory()}")
    return model, processor


def prepare_text(item):
    """문항 텍스트 준비"""
    content = item.get('content', {})
    question = content.get('question', '')
    choices = content.get('choices', [])

    text = f"문제: {question}"
    if choices:
        choices_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(choices)])
        text += f"\n선택지:\n{choices_text}"

    return text


def compute_similarity_matrix(embeddings):
    """임베딩으로 유사도 행렬 계산"""
    ids = list(embeddings.keys())
    vectors = np.array([embeddings[id] for id in ids])

    # L2 normalize
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / (norms + 1e-10)

    # Cosine similarity matrix
    sim_matrix = vectors @ vectors.T

    return ids, sim_matrix


def get_top_k_candidates(query_id, ids, sim_matrix, k=50):
    """쿼리에 대한 Top-K 후보 반환"""
    if query_id not in ids:
        return []

    query_idx = ids.index(query_id)
    similarities = sim_matrix[query_idx]

    indices = np.argsort(-similarities)
    candidates = []
    for idx in indices:
        if ids[idx] != query_id:
            candidates.append((ids[idx], float(similarities[idx])))
            if len(candidates) >= k:
                break

    return candidates


@torch.no_grad()
def rerank_pair(model, processor, query_text, doc_text):
    """쿼리-문서 쌍의 관련성 점수 계산"""
    instruction = "Given a math question, find similar questions with similar solution methods."

    # Reranker 입력 포맷
    messages = [
        {"role": "system", "content": [{"type": "text", "text": instruction}]},
        {"role": "user", "content": [
            {"type": "text", "text": f"Query: {query_text}\n\nDocument: {doc_text}"}
        ]}
    ]

    text_input = processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = processor(
        text=[text_input],
        padding=True,
        truncation=True,
        max_length=4096,
        return_tensors="pt"
    )
    inputs = {k: v.to(model.device) for k, v in inputs.items()}

    outputs = model(**inputs)
    score = torch.sigmoid(outputs.logits[0]).item()

    return score


def rerank_candidates(model, processor, query_item, candidate_items, items_dict):
    """후보 문항들 재순위화"""
    query_text = prepare_text(query_item)
    reranked = []

    for cand_id, emb_score in candidate_items:
        cand_item = items_dict.get(cand_id)
        if not cand_item:
            continue

        try:
            doc_text = prepare_text(cand_item)
            score = rerank_pair(model, processor, query_text, doc_text)
            reranked.append((cand_id, score))
        except Exception as e:
            # 실패시 임베딩 점수 사용
            reranked.append((cand_id, emb_score))

    reranked.sort(key=lambda x: -x[1])
    return reranked


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


def evaluate(results_by_query, ground_truth):
    """전체 평가 메트릭 계산"""
    metrics = {
        'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [],
        'mrr': [], 'ndcg_10': []
    }

    for query_id, predictions in results_by_query.items():
        gt_info = ground_truth.get(query_id)
        if not gt_info:
            continue

        relevant = gt_info['relevant']
        if not relevant:
            continue

        metrics['top_1'].append(top_k_recall(predictions, relevant, 1))
        metrics['top_3'].append(top_k_recall(predictions, relevant, 3))
        metrics['top_5'].append(top_k_recall(predictions, relevant, 5))
        metrics['top_10'].append(top_k_recall(predictions, relevant, 10))
        metrics['mrr'].append(mrr(predictions, relevant))
        metrics['ndcg_10'].append(ndcg_at_k(predictions, relevant, 10))

    return {k: float(np.mean(v)) * 100 if v else 0 for k, v in metrics.items()}


def load_ground_truth(gt_file):
    """Ground Truth 로드"""
    with open(gt_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    gt_dict = {}
    for gt in data['ground_truth']:
        query_id = gt['query_id']
        gt_dict[query_id] = {
            'category': gt.get('query_category', 'unknown'),
            'relevant': {r['id']: r.get('overall_score', r.get('relevance', 1))
                        for r in gt['relevant_items']}
        }
    return gt_dict


def main():
    print("=" * 70)
    print("Qwen3-VL-Reranker-8B 평가")
    print("=" * 70)

    # 1. 데이터 로드
    print("\n[1/5] 데이터 로드...")

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        items_data = json.load(f)
    items_dict = {item['id']: item for item in items_data['items']}
    print(f"      문항: {len(items_dict)}개")

    with open(EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
        emb_data = json.load(f)
    embeddings = emb_data['embeddings']
    print(f"      임베딩: {len(embeddings)}개")

    # Ground Truth 로드
    gt_files = {}
    for name, filepath in [("Image GT", IMAGE_GT_FILE), ("Hybrid GT", HYBRID_GT_FILE)]:
        if Path(filepath).exists():
            gt_files[name] = load_ground_truth(filepath)
            print(f"      {name}: {len(gt_files[name])} 쿼리")
        else:
            print(f"      {name}: 파일 없음")

    if not gt_files:
        print("Error: GT 파일이 없습니다.")
        return

    # 2. 유사도 행렬 계산
    print("\n[2/5] 임베딩 유사도 행렬 계산...")
    ids, sim_matrix = compute_similarity_matrix(embeddings)
    print(f"      행렬 크기: {sim_matrix.shape}")

    # 3. Embedding Only 평가
    print("\n[3/5] Embedding Only 검색...")
    embedding_results = {}

    all_query_ids = set()
    for gt in gt_files.values():
        all_query_ids.update(gt.keys())

    for query_id in tqdm(all_query_ids, desc="Embedding search"):
        if query_id in ids:
            candidates = get_top_k_candidates(query_id, ids, sim_matrix, k=TOP_K_CANDIDATES)
            embedding_results[query_id] = candidates

    # 4. Reranker 로드 및 적용
    print("\n[4/5] Reranker 적용...")
    model, processor = load_reranker()

    reranked_results = {}
    for query_id in tqdm(all_query_ids, desc="Reranking"):
        query_item = items_dict.get(query_id)
        candidates = embedding_results.get(query_id, [])

        if not query_item or not candidates:
            continue

        reranked = rerank_candidates(model, processor, query_item, candidates, items_dict)
        reranked_results[query_id] = reranked

    # 5. 평가 및 결과
    print("\n[5/5] 평가 결과")
    print("=" * 70)

    all_results = {}

    for gt_name, ground_truth in gt_files.items():
        print(f"\n### {gt_name} ###")

        emb_metrics = evaluate(embedding_results, ground_truth)
        rer_metrics = evaluate(reranked_results, ground_truth)

        print(f"\n{'Metric':<12} {'Embedding':<12} {'+ Reranker':<12} {'Change':<12}")
        print("-" * 50)

        for metric in ['top_1', 'top_3', 'top_5', 'top_10', 'mrr']:
            emb_val = emb_metrics[metric]
            rer_val = rer_metrics[metric]
            change = rer_val - emb_val
            sign = "+" if change >= 0 else ""
            print(f"{metric.upper():<12} {emb_val:>6.1f}%     {rer_val:>6.1f}%     {sign}{change:.1f}%p")

        all_results[gt_name] = {
            "embedding_only": emb_metrics,
            "with_reranker": rer_metrics,
            "improvement": {k: rer_metrics[k] - emb_metrics[k] for k in emb_metrics}
        }

    # 저장
    output = {
        "metadata": {
            "embedding_model": "Qwen/Qwen3-VL-Embedding-8B",
            "reranker_model": MODEL_NAME,
            "top_k_candidates": TOP_K_CANDIDATES,
            "created_at": datetime.now().isoformat()
        },
        "results": all_results
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {OUTPUT_FILE}")
    print(f"최종 GPU 메모리: {get_gpu_memory()}")

    print("\n" + "=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
