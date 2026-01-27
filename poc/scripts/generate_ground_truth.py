#!/usr/bin/env python3
"""
Task #6: Ground Truth 자동 생성
텍스트 유사도 기반으로 유사 문항 쌍을 자동 생성

방법:
1. TF-IDF + Cosine Similarity로 초기 유사도 계산
2. 메타데이터 유사성 (단원, 난이도) 가중치 적용
3. 상위 유사 문항을 Ground Truth로 지정
"""
import json
import re
from pathlib import Path
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Paths
POC_DATA_DIR = Path("/mnt/sda/worker/dev_ldm/iosys-generative/poc/data")
OUTPUT_FILE = POC_DATA_DIR / "ground_truth.json"

def load_test_items():
    """테스트 데이터 로드"""
    with open(POC_DATA_DIR / "test_items.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['items']

def preprocess_text(text):
    """텍스트 전처리"""
    if not text:
        return ""
    # LaTeX 수식 간소화
    text = re.sub(r'\$[^$]+\$', ' [수식] ', text)
    # 특수문자 제거
    text = re.sub(r'[^\w\s가-힣]', ' ', text)
    # 다중 공백 제거
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text_features(item):
    """문항에서 텍스트 특징 추출"""
    parts = []

    content = item.get('content', {})

    # 문제 텍스트
    question = content.get('question', '')
    parts.append(preprocess_text(question))

    # 선택지
    choices = content.get('choices', [])
    for choice in choices:
        parts.append(preprocess_text(choice))

    # 해설
    explanation = content.get('explanation', '')
    parts.append(preprocess_text(explanation))

    return ' '.join(parts)

def calculate_metadata_similarity(item1, item2):
    """메타데이터 기반 유사도 계산"""
    meta1 = item1.get('metadata', {})
    meta2 = item2.get('metadata', {})

    score = 0.0
    weights = {
        'unit_small': 0.4,   # 소단원 일치
        'unit_medium': 0.3,  # 중단원 일치
        'unit_large': 0.2,   # 대단원 일치
        'difficulty': 0.1,   # 난이도 일치
    }

    for field, weight in weights.items():
        if meta1.get(field) and meta2.get(field):
            if meta1[field] == meta2[field]:
                score += weight

    return score

def calculate_similarity_matrix(items):
    """TF-IDF 기반 유사도 행렬 계산"""
    print("  텍스트 특징 추출...")
    texts = [extract_text_features(item) for item in items]

    print("  TF-IDF 벡터화...")
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=1
    )
    tfidf_matrix = vectorizer.fit_transform(texts)

    print("  코사인 유사도 계산...")
    similarity_matrix = cosine_similarity(tfidf_matrix)

    return similarity_matrix

def generate_ground_truth(items, similarity_matrix, top_k=5, min_similarity=0.1):
    """Ground Truth 생성"""
    ground_truth = []
    n = len(items)

    for i in range(n):
        query_item = items[i]
        query_id = query_item['id']

        # 유사도 점수 계산 (텍스트 + 메타데이터)
        scores = []
        for j in range(n):
            if i == j:
                continue

            text_sim = similarity_matrix[i, j]
            meta_sim = calculate_metadata_similarity(query_item, items[j])

            # 가중 합산 (텍스트 70%, 메타데이터 30%)
            combined_score = 0.7 * text_sim + 0.3 * meta_sim

            if combined_score >= min_similarity:
                scores.append((j, combined_score))

        # 상위 K개 선택
        scores.sort(key=lambda x: -x[1])
        top_items = scores[:top_k]

        # Relevance score 할당
        # 상위 1-2: relevance 3 (매우 유사)
        # 상위 3-4: relevance 2 (유사)
        # 상위 5: relevance 1 (관련)
        relevant_items = []
        for rank, (j, score) in enumerate(top_items):
            if rank < 2:
                relevance = 3
            elif rank < 4:
                relevance = 2
            else:
                relevance = 1

            relevant_items.append({
                "id": items[j]['id'],
                "relevance": relevance,
                "similarity_score": round(score, 4)
            })

        if relevant_items:
            ground_truth.append({
                "query_id": query_id,
                "query_category": categorize_item(query_item),
                "relevant_items": relevant_items
            })

    return ground_truth

def categorize_item(item):
    """문항 카테고리 분류"""
    has_image = item.get('has_image', False)
    has_latex = len(item.get('content', {}).get('question_latex', [])) > 0

    if has_image:
        return "image"
    elif has_latex:
        return "latex"
    else:
        return "text_only"

def main():
    print("=" * 60)
    print("Ground Truth 자동 생성")
    print("=" * 60)

    # 데이터 로드
    print("\n[1/4] 테스트 데이터 로드...")
    items = load_test_items()
    print(f"      문항 수: {len(items)}")

    # 유사도 행렬 계산
    print("\n[2/4] 유사도 행렬 계산...")
    similarity_matrix = calculate_similarity_matrix(items)

    # Ground Truth 생성
    print("\n[3/4] Ground Truth 생성...")
    ground_truth = generate_ground_truth(
        items,
        similarity_matrix,
        top_k=5,
        min_similarity=0.05
    )

    # 통계
    total_pairs = sum(len(gt['relevant_items']) for gt in ground_truth)
    relevance_counts = defaultdict(int)
    for gt in ground_truth:
        for rel in gt['relevant_items']:
            relevance_counts[rel['relevance']] += 1

    print(f"      총 쿼리: {len(ground_truth)}")
    print(f"      총 유사 쌍: {total_pairs}")
    print(f"      Relevance 분포: {dict(relevance_counts)}")

    # 저장
    print("\n[4/4] 저장...")
    output_data = {
        "metadata": {
            "total_queries": len(ground_truth),
            "total_pairs": total_pairs,
            "relevance_distribution": dict(relevance_counts),
            "generation_method": "TF-IDF + Metadata Similarity",
            "top_k": 5,
            "min_similarity": 0.05
        },
        "ground_truth": ground_truth
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"      저장: {OUTPUT_FILE}")

    # 샘플 출력
    print("\n" + "=" * 60)
    print("샘플 Ground Truth (처음 3개)")
    print("=" * 60)
    for gt in ground_truth[:3]:
        query_item = next(i for i in items if i['id'] == gt['query_id'])
        question = query_item['content']['question'][:50]
        print(f"\nQuery: {gt['query_id']}")
        print(f"Category: {gt['query_category']}")
        print(f"Question: {question}...")
        print(f"Relevant items:")
        for rel in gt['relevant_items']:
            print(f"  - {rel['id']} (relevance={rel['relevance']}, score={rel['similarity_score']})")

    print("\n" + "=" * 60)
    print("Ground Truth 생성 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
