#!/usr/bin/env python3
"""
04_validate.py
전처리 데이터 유효성 검증

Usage:
    python scripts/04_validate.py
"""

import json
import re
import os
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Any, Tuple

# Constants
SCRIPT_DIR = Path(__file__).parent
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
PARTS_DIR = OUTPUT_DIR / "parts"
DATA_DIR = SCRIPT_DIR.parent.parent / "data" / "raw"


def load_all_items() -> List[Dict[str, Any]]:
    """모든 파트 파일에서 아이템 로드"""
    items = []
    part_files = sorted(PARTS_DIR.glob("items_part*.json"))

    for part_file in part_files:
        with open(part_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            items.extend(data.get('items', []))

    return items


def validate_metadata(item: Dict) -> List[str]:
    """메타데이터 유효성 검증"""
    errors = []
    meta = item.get('metadata', {})

    # 필수 메타데이터
    required_fields = ['difficulty', 'question_type', 'grade', 'subject']
    for field in required_fields:
        if not meta.get(field):
            errors.append(f"missing_metadata_{field}")

    # 난이도 값 검증
    valid_difficulties = ['상', '상중', '중', '중하', '하', '']
    if meta.get('difficulty') and meta['difficulty'] not in valid_difficulties:
        errors.append(f"invalid_difficulty:{meta['difficulty']}")

    # 문항유형 값 검증
    valid_types = ['선택형', '단답형', '완결형', '서술형', '']
    if meta.get('question_type') and meta['question_type'] not in valid_types:
        errors.append(f"invalid_question_type:{meta['question_type']}")

    # 학기 값 검증
    valid_semesters = ['1학기', '2학기', '']
    if meta.get('semester') and meta['semester'] not in valid_semesters:
        errors.append(f"invalid_semester:{meta['semester']}")

    # 연도 범위 검증
    year = meta.get('year')
    if year and (year < 2000 or year > 2030):
        errors.append(f"invalid_year:{year}")

    return errors


def validate_content(item: Dict) -> List[str]:
    """콘텐츠 유효성 검증"""
    errors = []
    content = item.get('content', {})
    meta = item.get('metadata', {})

    # 문제 텍스트 검증
    question = content.get('question', '')
    if not question:
        errors.append("empty_question")
    elif len(question) < 5:
        errors.append("question_too_short")

    # 선택형 문항 검증
    if meta.get('question_type') == '선택형':
        choices = content.get('choices', [])

        # 선택지 개수 검증
        if len(choices) == 0:
            errors.append("no_choices")
        elif len(choices) < 4:
            errors.append(f"insufficient_choices:{len(choices)}")
        elif len(choices) > 5:
            errors.append(f"too_many_choices:{len(choices)}")

        # 정답 검증 (단일 또는 복수)
        answer = content.get('answer')
        answers = content.get('answers', [])

        if answer is None and not answers:
            errors.append("missing_answer")
        elif answers:
            # 복수 정답 검증
            for ans in answers:
                if not isinstance(ans, int):
                    errors.append(f"invalid_answer_type:{type(ans).__name__}")
                elif ans < 1 or ans > len(choices):
                    errors.append(f"answer_out_of_range:{ans}")
        elif answer is not None:
            # 단일 정답 검증
            if not isinstance(answer, int):
                errors.append(f"invalid_answer_type:{type(answer).__name__}")
            elif answer < 1 or answer > len(choices):
                errors.append(f"answer_out_of_range:{answer}")

        # 빈 선택지 검증
        empty_choices = [i+1 for i, c in enumerate(choices) if not c.strip()]
        if empty_choices:
            errors.append(f"empty_choices:{empty_choices}")

    # 단답형/완결형 문항 검증
    elif meta.get('question_type') in ['단답형', '완결형']:
        answer_text = content.get('answer_text', '')
        if not answer_text:
            errors.append("missing_answer_text")

    # LaTeX 수식 검증
    question_latex = content.get('question_latex', [])
    for i, latex in enumerate(question_latex):
        if latex:
            # 중괄호 균형 검사
            if latex.count('{') != latex.count('}'):
                errors.append(f"unbalanced_braces_in_latex:{i}")

    return errors


def validate_images(item: Dict) -> List[str]:
    """이미지 유효성 검증"""
    errors = []
    images = item.get('images', {})
    source_file = item.get('_source_file', '')

    # 이미지 경로 검증
    all_images = images.get('question', []) + images.get('explanation', [])

    for img_path in all_images:
        if not img_path:
            errors.append("empty_image_path")
            continue

        # 경로 형식 검증
        if '\\' in img_path:
            errors.append(f"windows_path_format:{img_path[:30]}")

        # 확장자 검증
        ext = Path(img_path).suffix.lower()
        if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            errors.append(f"invalid_image_extension:{ext}")

        # 실제 파일 존재 검증
        if source_file:
            source_path = Path(source_file)
            if source_path.parts[0] == 'data':
                full_path = DATA_DIR.parent / source_path.parent / img_path
            else:
                full_path = source_path.parent / img_path

            if not full_path.exists():
                errors.append(f"image_not_found:{img_path[:50]}")

    # 누락된 이미지 확인
    missing = images.get('missing', [])
    if missing:
        errors.append(f"missing_images_count:{len(missing)}")

    return errors


def validate_consistency(item: Dict) -> List[str]:
    """일관성 검증"""
    errors = []
    content = item.get('content', {})

    # 문제에 [이미지] 플레이스홀더가 있는데 이미지가 없는 경우
    question = content.get('question', '')
    images = item.get('images', {})
    question_images = images.get('question', [])

    if '[이미지]' in question and not question_images:
        errors.append("image_placeholder_without_image")

    if question_images and '[이미지]' not in question:
        errors.append("image_without_placeholder")

    # 해설에 [이미지] 플레이스홀더가 있는데 이미지가 없는 경우
    explanation = content.get('explanation', '')
    explanation_images = images.get('explanation', [])

    if '[이미지]' in explanation and not explanation_images:
        errors.append("explanation_image_placeholder_without_image")

    return errors


def validate_duplicates(items: List[Dict]) -> Dict[str, List[str]]:
    """중복 검사"""
    duplicates = {
        'duplicate_ids': [],
        'duplicate_questions': []
    }

    # ID 중복 검사
    id_counts = defaultdict(list)
    for i, item in enumerate(items):
        item_id = item.get('id', '')
        if item_id:
            id_counts[item_id].append(i)

    for item_id, indices in id_counts.items():
        if len(indices) > 1:
            duplicates['duplicate_ids'].append({
                'id': item_id,
                'count': len(indices),
                'indices': indices[:5]  # 처음 5개만
            })

    # 문제 텍스트 중복 검사 (정확히 같은 경우)
    question_counts = defaultdict(list)
    for i, item in enumerate(items):
        question = item.get('content', {}).get('question', '')
        if question and len(question) > 20:  # 짧은 문제는 제외
            # 공백 정규화 후 비교
            normalized = ' '.join(question.split())
            question_counts[normalized].append(i)

    for question, indices in question_counts.items():
        if len(indices) > 1:
            duplicates['duplicate_questions'].append({
                'question': question[:100] + '...' if len(question) > 100 else question,
                'count': len(indices),
                'indices': indices[:5]
            })

    return duplicates


def run_validation(items: List[Dict]) -> Dict[str, Any]:
    """전체 유효성 검증 실행"""
    results = {
        'total_items': len(items),
        'valid_items': 0,
        'invalid_items': 0,
        'errors_by_type': defaultdict(int),
        'errors_by_item': [],
        'sample_errors': [],
        'duplicates': {}
    }

    for i, item in enumerate(items):
        item_errors = []

        # 각 검증 실행
        item_errors.extend(validate_metadata(item))
        item_errors.extend(validate_content(item))
        item_errors.extend(validate_images(item))
        item_errors.extend(validate_consistency(item))

        if item_errors:
            results['invalid_items'] += 1
            results['errors_by_item'].append({
                'index': i,
                'id': item.get('id', ''),
                'errors': item_errors
            })

            for err in item_errors:
                err_type = err.split(':')[0]
                results['errors_by_type'][err_type] += 1

            # 샘플 에러 수집 (처음 10개)
            if len(results['sample_errors']) < 10:
                results['sample_errors'].append({
                    'id': item.get('id', ''),
                    'errors': item_errors,
                    'question_preview': item.get('content', {}).get('question', '')[:100]
                })
        else:
            results['valid_items'] += 1

    # 중복 검사
    results['duplicates'] = validate_duplicates(items)

    # defaultdict를 일반 dict로 변환
    results['errors_by_type'] = dict(results['errors_by_type'])

    return results


def main():
    print("=" * 60)
    print("Data Validation")
    print("=" * 60)

    # 데이터 로드
    print(f"\n[1/3] Loading data from {PARTS_DIR}...")
    items = load_all_items()
    print(f"      Loaded {len(items):,} items")

    # 유효성 검증
    print(f"\n[2/3] Running validation...")
    results = run_validation(items)

    # 결과 저장
    print(f"\n[3/3] Saving validation report...")
    report_file = OUTPUT_DIR / "validation_report.json"

    # errors_by_item은 너무 클 수 있으므로 요약만 저장
    save_results = {
        'total_items': results['total_items'],
        'valid_items': results['valid_items'],
        'invalid_items': results['invalid_items'],
        'validation_rate': f"{results['valid_items']/results['total_items']*100:.2f}%",
        'errors_by_type': results['errors_by_type'],
        'sample_errors': results['sample_errors'],
        'duplicates': {
            'duplicate_id_count': len(results['duplicates']['duplicate_ids']),
            'duplicate_question_count': len(results['duplicates']['duplicate_questions']),
            'duplicate_ids': results['duplicates']['duplicate_ids'][:10],
            'duplicate_questions': results['duplicates']['duplicate_questions'][:10]
        }
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(save_results, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {report_file}")

    # 결과 출력
    print("\n" + "=" * 60)
    print("Validation Summary")
    print("=" * 60)
    print(f"  Total items: {results['total_items']:,}")
    print(f"  Valid items: {results['valid_items']:,} ({results['valid_items']/results['total_items']*100:.1f}%)")
    print(f"  Invalid items: {results['invalid_items']:,} ({results['invalid_items']/results['total_items']*100:.1f}%)")

    if results['errors_by_type']:
        print(f"\n  Errors by Type:")
        for err_type, count in sorted(results['errors_by_type'].items(), key=lambda x: -x[1]):
            print(f"    - {err_type}: {count:,}")

    dup = results['duplicates']
    if dup['duplicate_ids'] or dup['duplicate_questions']:
        print(f"\n  Duplicates:")
        print(f"    - Duplicate IDs: {len(dup['duplicate_ids']):,}")
        print(f"    - Duplicate Questions: {len(dup['duplicate_questions']):,}")

    if results['sample_errors']:
        print(f"\n  Sample Errors (first 3):")
        for sample in results['sample_errors'][:3]:
            print(f"    ID: {sample['id']}")
            print(f"    Errors: {sample['errors']}")
            print(f"    Question: {sample['question_preview'][:60]}...")
            print()

    print("=" * 60)
    print("Validation completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
