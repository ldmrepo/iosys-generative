#!/usr/bin/env python3
"""
Task #5: 수학 테스트 데이터 100건 샘플링
- 이미지형 35건
- 텍스트형 35건
- LaTeX형 30건
"""
import json
import random
from pathlib import Path
from collections import defaultdict

# Paths
DATA_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/data/processed")
OUTPUT_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_all_items():
    """모든 전처리된 문항 로드"""
    items = []
    for part_file in sorted(DATA_DIR.glob("items_part*.json")):
        with open(part_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            items.extend(data.get('items', []))
    return items

def categorize_items(items):
    """문항을 이미지형/텍스트형/LaTeX형으로 분류"""
    categories = {
        'image': [],      # 이미지 포함 문항
        'text_only': [],  # 순수 텍스트 문항 (LaTeX 없음)
        'latex': [],      # LaTeX 수식 포함 문항 (이미지 없음)
    }

    for item in items:
        has_image = item.get('has_image', False)
        question_latex = item.get('content', {}).get('question_latex', [])
        has_latex = len(question_latex) > 0

        if has_image:
            categories['image'].append(item)
        elif has_latex:
            categories['latex'].append(item)
        else:
            categories['text_only'].append(item)

    return categories

def stratified_sample(categories, target_counts):
    """층화 샘플링"""
    sampled = []

    for cat_name, count in target_counts.items():
        pool = categories[cat_name]
        if len(pool) < count:
            print(f"Warning: {cat_name} has only {len(pool)} items, requested {count}")
            sampled.extend(pool)
        else:
            # 난이도 분포를 고려한 샘플링
            by_difficulty = defaultdict(list)
            for item in pool:
                diff = item.get('metadata', {}).get('difficulty', '중')
                by_difficulty[diff].append(item)

            # 각 난이도에서 균등하게 샘플링 시도
            per_diff = max(1, count // len(by_difficulty))
            selected = []
            for diff, diff_items in by_difficulty.items():
                n = min(per_diff, len(diff_items))
                selected.extend(random.sample(diff_items, n))

            # 부족하면 전체에서 추가 샘플링
            remaining = count - len(selected)
            if remaining > 0:
                remaining_pool = [i for i in pool if i not in selected]
                if remaining_pool:
                    selected.extend(random.sample(remaining_pool, min(remaining, len(remaining_pool))))

            sampled.extend(selected[:count])

    return sampled

def main():
    print("=" * 60)
    print("테스트 데이터 샘플링")
    print("=" * 60)

    # 시드 고정 (재현성)
    random.seed(42)

    # 데이터 로드
    print("\n[1/4] 전처리 데이터 로드...")
    items = load_all_items()
    print(f"      총 문항: {len(items):,}개")

    # 분류
    print("\n[2/4] 문항 분류...")
    categories = categorize_items(items)
    for cat, cat_items in categories.items():
        print(f"      {cat}: {len(cat_items):,}개")

    # 샘플링
    print("\n[3/4] 층화 샘플링...")
    target_counts = {
        'image': 35,
        'text_only': 35,
        'latex': 30,
    }
    sampled = stratified_sample(categories, target_counts)
    print(f"      샘플링 완료: {len(sampled)}개")

    # 통계 출력
    print("\n      샘플 통계:")
    sampled_cats = categorize_items(sampled)
    for cat, cat_items in sampled_cats.items():
        print(f"        - {cat}: {len(cat_items)}개")

    # 난이도 분포
    diff_counts = defaultdict(int)
    for item in sampled:
        diff = item.get('metadata', {}).get('difficulty', '중')
        diff_counts[diff] += 1
    print(f"      난이도 분포: {dict(diff_counts)}")

    # 문항 유형 분포
    type_counts = defaultdict(int)
    for item in sampled:
        qtype = item.get('metadata', {}).get('question_type', '기타')
        type_counts[qtype] += 1
    print(f"      문항 유형: {dict(type_counts)}")

    # 저장
    print("\n[4/4] 저장...")
    output_file = OUTPUT_DIR / "test_items.json"

    output_data = {
        "metadata": {
            "total_items": len(sampled),
            "sampling_seed": 42,
            "categories": {
                "image": len(sampled_cats['image']),
                "text_only": len(sampled_cats['text_only']),
                "latex": len(sampled_cats['latex']),
            },
            "difficulty_distribution": dict(diff_counts),
            "question_type_distribution": dict(type_counts),
        },
        "items": sampled
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"      저장: {output_file}")

    # ID 목록도 저장 (참조용)
    id_list_file = OUTPUT_DIR / "test_item_ids.txt"
    with open(id_list_file, 'w') as f:
        for item in sampled:
            f.write(item['id'] + '\n')
    print(f"      ID 목록: {id_list_file}")

    print("\n" + "=" * 60)
    print("샘플링 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
