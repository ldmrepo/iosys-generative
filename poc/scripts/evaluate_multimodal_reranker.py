#!/usr/bin/env python3
"""
멀티모달 임베딩 + Qwen3-VL-Reranker 조합 평가
Image GT 기준으로 평가
"""
import json
import sys
import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm

# Paths
POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
MODEL_PATH = POC_DIR / "models/qwen3-vl-reranker-2b"
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")

# Add model scripts to path
sys.path.insert(0, str(MODEL_PATH / "scripts"))


def get_gpu_memory():
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1e9
        return f"{allocated:.2f}GB"
    return "N/A"


def find_image_path(item):
    """문항의 이미지 경로 찾기"""
    images = item.get('images', {})
    image_candidates = images.get('question', []) or images.get('explanation', [])

    if not image_candidates:
        return None

    img_path = image_candidates[0]

    direct_path = RAW_IMAGE_DIR / img_path
    if direct_path.exists():
        return direct_path

    for folder in RAW_IMAGE_DIR.iterdir():
        if not folder.is_dir() or not folder.name.isdigit():
            continue

        if len(folder.name) == 8:
            candidate = folder / img_path
            if candidate.exists():
                return candidate
        elif len(folder.name) == 4:
            for month_folder in folder.iterdir():
                if not month_folder.is_dir():
                    continue
                for day_folder in month_folder.iterdir():
                    if not day_folder.is_dir():
                        continue
                    candidate = day_folder / img_path
                    if candidate.exists():
                        return candidate

    return None


def get_item_text(item):
    """문항 텍스트 추출"""
    content = item.get('content', {})
    question = content.get('question', '')
    choices = content.get('choices', [])

    text = f"문제: {question}"
    if choices:
        choices_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(choices)])
        text += f"\n선택지:\n{choices_text}"

    return text


def load_embeddings():
    """멀티모달 임베딩 로드 (mean pooling)"""
    with open(RESULTS_DIR / "qwen_embeddings_multimodal_meanpool.json", 'r') as f:
        data = json.load(f)
    return data['embeddings']


def load_test_items():
    """테스트 문항 로드"""
    with open(DATA_DIR / "test_items.json", 'r') as f:
        data = json.load(f)
    return {item['id']: item for item in data['items']}


def load_image_gt():
    """Image GT 로드"""
    with open(DATA_DIR / "ground_truth_image.json", 'r') as f:
        data = json.load(f)

    gt_dict = {}
    for gt in data['ground_truth']:
        query_id = gt['query_id']
        gt_dict[query_id] = {
            'category': gt['query_category'],
            'relevant': {r['id']: r['overall_score'] for r in gt['relevant_items']}
        }
    return gt_dict, data.get('metadata', {})


def compute_similarity_matrix(embeddings):
    """임베딩으로 유사도 행렬 계산"""
    ids = list(embeddings.keys())
    vectors = np.array([embeddings[id] for id in ids])

    # L2 normalize
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / norms

    # Cosine similarity matrix
    sim_matrix = vectors @ vectors.T

    return ids, sim_matrix


def get_top_k_candidates(query_id, ids, sim_matrix, k=50):
    """쿼리에 대한 Top-K 후보 반환"""
    if query_id not in ids:
        return []

    query_idx = ids.index(query_id)
    similarities = sim_matrix[query_idx]

    # 자기 자신 제외하고 정렬
    indices = np.argsort(-similarities)
    candidates = []
    for idx in indices:
        if ids[idx] != query_id:
            candidates.append((ids[idx], float(similarities[idx])))
            if len(candidates) >= k:
                break

    return candidates


def load_reranker():
    """Reranker 모델 로드"""
    from qwen3_vl_reranker import Qwen3VLReranker

    print(f"Loading Reranker from {MODEL_PATH}...")
    print(f"Initial GPU memory: {get_gpu_memory()}")

    model = Qwen3VLReranker(
        model_name_or_path=str(MODEL_PATH),
        torch_dtype=torch.float16,
        default_instruction="Given a math question, find similar questions with similar images and solution methods."
    )

    print(f"Reranker loaded. GPU memory: {get_gpu_memory()}")
    return model


def rerank_candidates(reranker, query_item, candidate_items, items_dict):
    """Reranker로 후보 재순위화"""
    # Query 준비
    query_text = get_item_text(query_item)
    query_image = find_image_path(query_item)

    query = {
        'text': query_text,
    }
    if query_image:
        query['image'] = str(query_image)

    # Documents 준비
    documents = []
    for cand_id, _ in candidate_items:
        cand_item = items_dict.get(cand_id)
        if not cand_item:
            continue

        doc = {
            'text': get_item_text(cand_item),
        }
        cand_image = find_image_path(cand_item)
        if cand_image:
            doc['image'] = str(cand_image)

        documents.append((cand_id, doc))

    if not documents:
        return []

    # Reranker 실행
    inputs = {
        'query': query,
        'documents': [doc for _, doc in documents]
    }

    try:
        scores = reranker.process(inputs)

        # 점수와 ID 결합
        reranked = [(documents[i][0], scores[i]) for i in range(len(scores))]
        reranked.sort(key=lambda x: -x[1])

        return reranked
    except Exception as e:
        print(f"Reranker error: {e}")
        return [(cid, sim) for cid, sim in candidate_items]


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

    ideal_relevances = sorted(ground_truth.values(), reverse=True)[:k]
    idcg = sum(rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevances))

    return dcg / idcg if idcg > 0 else 0


def evaluate(results_by_query, ground_truth):
    """전체 평가 메트릭 계산"""
    metrics = {
        'top_1': [], 'top_3': [], 'top_5': [], 'top_10': [], 'top_20': [],
        'mrr': [], 'ndcg_5': [], 'ndcg_10': []
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
        metrics['top_20'].append(top_k_recall(predictions, relevant, 20))
        metrics['mrr'].append(mrr(predictions, relevant))
        metrics['ndcg_5'].append(ndcg_at_k(predictions, relevant, 5))
        metrics['ndcg_10'].append(ndcg_at_k(predictions, relevant, 10))

    return {k: float(np.mean(v)) if v else 0 for k, v in metrics.items()}


def main():
    print("=" * 70)
    print("멀티모달 임베딩 + Reranker 평가 (Image GT)")
    print("=" * 70)

    # 1. 데이터 로드
    print("\n[1/5] 데이터 로드...")
    embeddings = load_embeddings()
    items_dict = load_test_items()
    ground_truth, gt_meta = load_image_gt()

    print(f"      임베딩: {len(embeddings)}개")
    print(f"      문항: {len(items_dict)}개")
    print(f"      GT 쿼리: {len(ground_truth)}개")
    print(f"      GT 유사 쌍: {gt_meta.get('total_relevant_pairs', 'N/A')}개")

    # 2. 유사도 행렬 계산
    print("\n[2/5] 임베딩 유사도 행렬 계산...")
    ids, sim_matrix = compute_similarity_matrix(embeddings)
    print(f"      행렬 크기: {sim_matrix.shape}")

    # 3. Embedding Only 평가 (비교용)
    print("\n[3/5] Embedding Only 검색...")
    embedding_results = {}
    for query_id in tqdm(ground_truth.keys(), desc="Embedding search"):
        candidates = get_top_k_candidates(query_id, ids, sim_matrix, k=50)
        embedding_results[query_id] = candidates

    embedding_metrics = evaluate(embedding_results, ground_truth)

    print(f"\n      Embedding Only 결과:")
    print(f"        Top-5 Recall:  {embedding_metrics['top_5']*100:.1f}%")
    print(f"        Top-10 Recall: {embedding_metrics['top_10']*100:.1f}%")
    print(f"        MRR:           {embedding_metrics['mrr']*100:.1f}%")

    # 4. Reranker 적용
    print("\n[4/5] Reranker 적용...")
    reranker = load_reranker()

    reranked_results = {}
    for query_id in tqdm(ground_truth.keys(), desc="Reranking"):
        query_item = items_dict.get(query_id)
        if not query_item:
            continue

        # Embedding 결과에서 Top-50 후보
        candidates = embedding_results.get(query_id, [])
        if not candidates:
            continue

        # Reranker로 재순위화
        reranked = rerank_candidates(reranker, query_item, candidates, items_dict)
        reranked_results[query_id] = reranked

    reranked_metrics = evaluate(reranked_results, ground_truth)

    # 5. 결과 출력
    print("\n[5/5] 결과 비교")
    print("=" * 70)

    print(f"\n{'Metric':<15} {'Embedding Only':<20} {'+ Reranker':<20} {'Change':<15}")
    print("-" * 70)

    for metric in ['top_1', 'top_3', 'top_5', 'top_10', 'mrr', 'ndcg_5', 'ndcg_10']:
        emb_val = embedding_metrics[metric]
        rer_val = reranked_metrics[metric]
        change = rer_val - emb_val
        sign = "+" if change >= 0 else ""

        label = metric.replace('_', '-').upper()
        print(f"{label:<15} {emb_val*100:.1f}%{'':<16} {rer_val*100:.1f}%{'':<16} {sign}{change*100:.1f}%p")

    # 결과 저장
    output = {
        "experiment": "Multimodal Embedding + Reranker",
        "ground_truth": "Image GT (GPT-4o)",
        "embedding_model": "Qwen3-VL-Embedding-2B (multimodal, mean pooling)",
        "reranker_model": "Qwen3-VL-Reranker-2B",
        "total_queries": len(ground_truth),
        "results": {
            "embedding_only": embedding_metrics,
            "with_reranker": reranked_metrics,
            "improvement": {
                k: reranked_metrics[k] - embedding_metrics[k]
                for k in embedding_metrics
            }
        }
    }

    output_file = RESULTS_DIR / "multimodal_reranker_evaluation.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_file}")

    # 요약
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    top5_imp = output["results"]["improvement"]["top_5"] * 100
    top10_imp = output["results"]["improvement"]["top_10"] * 100
    mrr_imp = output["results"]["improvement"]["mrr"] * 100

    print(f"\nTop-5 Recall:  {embedding_metrics['top_5']*100:.1f}% → {reranked_metrics['top_5']*100:.1f}% ({'+' if top5_imp >= 0 else ''}{top5_imp:.1f}%p)")
    print(f"Top-10 Recall: {embedding_metrics['top_10']*100:.1f}% → {reranked_metrics['top_10']*100:.1f}% ({'+' if top10_imp >= 0 else ''}{top10_imp:.1f}%p)")
    print(f"MRR:           {embedding_metrics['mrr']*100:.1f}% → {reranked_metrics['mrr']*100:.1f}% ({'+' if mrr_imp >= 0 else ''}{mrr_imp:.1f}%p)")

    print("\n" + "=" * 70)
    print("완료!")
    print("=" * 70)


if __name__ == "__main__":
    main()
