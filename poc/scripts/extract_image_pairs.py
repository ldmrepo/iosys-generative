#!/usr/bin/env python3
"""
Task #1: 이미지 문항 쌍 추출
이미지 GT 생성을 위한 비교 쌍 추출
"""
import json
import numpy as np
from pathlib import Path
from itertools import combinations

POC_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc")
DATA_DIR = POC_DIR / "data"
RESULTS_DIR = POC_DIR / "results"
RAW_IMAGE_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/raw")


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


def load_data():
    """데이터 로드"""
    with open(DATA_DIR / "test_items.json", 'r', encoding='utf-8') as f:
        items = json.load(f)['items']

    # 멀티모달 임베딩 로드 (유사도 기반 필터링용)
    with open(RESULTS_DIR / "qwen_embeddings_multimodal_meanpool.json", 'r', encoding='utf-8') as f:
        emb_data = json.load(f)

    return items, emb_data['embeddings']


def get_image_items(items):
    """이미지 문항만 추출"""
    image_items = []
    for item in items:
        if item.get('has_image'):
            img_path = find_image_path(item)
            if img_path:
                image_items.append({
                    'id': item['id'],
                    'item': item,
                    'image_path': str(img_path)
                })
    return image_items


def compute_similarity_matrix(image_items, embeddings):
    """임베딩 기반 유사도 행렬 계산"""
    ids = [item['id'] for item in image_items]

    # 임베딩 추출
    emb_list = []
    for item_id in ids:
        if item_id in embeddings:
            emb_list.append(embeddings[item_id])
        else:
            emb_list.append([0] * 2048)

    emb_matrix = np.array(emb_list)
    emb_matrix = emb_matrix / np.linalg.norm(emb_matrix, axis=1, keepdims=True)

    # 코사인 유사도 행렬
    sim_matrix = emb_matrix @ emb_matrix.T

    return ids, sim_matrix


def extract_pairs(image_items, embeddings, top_k=10):
    """비교 쌍 추출 - 각 문항당 Top-K 유사 문항"""
    ids, sim_matrix = compute_similarity_matrix(image_items, embeddings)
    id_to_item = {item['id']: item for item in image_items}

    pairs = []
    seen = set()

    for i, item_id_a in enumerate(ids):
        # 자기 자신 제외, 유사도 높은 순으로 정렬
        similarities = [(j, sim_matrix[i, j]) for j in range(len(ids)) if i != j]
        similarities.sort(key=lambda x: -x[1])

        # Top-K 추출
        for j, sim in similarities[:top_k]:
            item_id_b = ids[j]

            # 중복 방지 (A-B와 B-A는 같은 쌍)
            pair_key = tuple(sorted([item_id_a, item_id_b]))
            if pair_key in seen:
                continue
            seen.add(pair_key)

            item_a = id_to_item[item_id_a]
            item_b = id_to_item[item_id_b]

            pairs.append({
                'item_a': {
                    'id': item_id_a,
                    'text': get_item_text(item_a['item']),
                    'image_path': item_a['image_path'],
                    'metadata': get_item_metadata(item_a['item'])
                },
                'item_b': {
                    'id': item_id_b,
                    'text': get_item_text(item_b['item']),
                    'image_path': item_b['image_path'],
                    'metadata': get_item_metadata(item_b['item'])
                },
                'embedding_similarity': float(sim)
            })

    return pairs


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


def get_item_metadata(item):
    """문항 메타데이터 추출"""
    meta = item.get('metadata', {})
    return {
        'subject': meta.get('subject', ''),
        'grade': meta.get('grade', ''),
        'unit_large': meta.get('unit_large', ''),
        'unit_medium': meta.get('unit_medium', ''),
        'difficulty': meta.get('difficulty', '')
    }


def main():
    print("=" * 60)
    print("이미지 문항 쌍 추출")
    print("=" * 60)

    # 데이터 로드
    print("\n[1/4] 데이터 로드...")
    items, embeddings = load_data()
    print(f"      전체 문항: {len(items)}")

    # 이미지 문항 추출
    print("\n[2/4] 이미지 문항 추출...")
    image_items = get_image_items(items)
    print(f"      이미지 문항: {len(image_items)}")

    # 전수 비교 쌍 수
    total_pairs = len(image_items) * (len(image_items) - 1) // 2
    print(f"      전수 비교 시 쌍 수: {total_pairs}")

    # 쌍 추출 (각 문항당 Top-10 유사 문항)
    print("\n[3/4] 비교 쌍 추출 (Top-10 유사도 기준)...")
    pairs = extract_pairs(image_items, embeddings, top_k=10)
    print(f"      추출된 쌍: {len(pairs)}")

    # 유사도 분포
    similarities = [p['embedding_similarity'] for p in pairs]
    print(f"      유사도 범위: {min(similarities):.3f} ~ {max(similarities):.3f}")
    print(f"      유사도 평균: {np.mean(similarities):.3f}")

    # 저장
    print("\n[4/4] 저장...")
    output = {
        'metadata': {
            'total_image_items': len(image_items),
            'total_pairs': len(pairs),
            'selection_method': 'Top-10 embedding similarity per item',
            'embedding_model': 'Qwen3-VL-Embedding-2B (multimodal, mean pooling)'
        },
        'pairs': pairs
    }

    output_file = DATA_DIR / "image_pairs_for_gt.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"      저장: {output_file}")

    print("\n" + "=" * 60)
    print(f"완료! {len(pairs)}개 쌍 추출")
    print("=" * 60)


if __name__ == "__main__":
    main()
