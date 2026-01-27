#!/usr/bin/env python3
"""
03_preprocess.py
파싱된 데이터 전처리 및 최종 출력 생성

Usage:
    python scripts/03_preprocess.py
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent / "utils"))
from latex_cleaner import clean_latex as latex_cleaner_clean, clean_latex_in_text

# Constants
SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"
OUTPUT_DIR = SCRIPT_DIR.parent / "output"
INPUT_FILE = OUTPUT_DIR / "items_parsed.json"


def clean_text(text: str) -> str:
    """텍스트 정제 (LaTeX는 파싱 단계에서 이미 정규화됨)"""
    if not text:
        return ""

    # 연속 공백을 단일 공백으로
    text = re.sub(r'\s+', ' ', text)

    # 앞뒤 공백 제거
    text = text.strip()

    # [이미지] 플레이스홀더 주변 정리
    text = re.sub(r'\s*\[이미지\]\s*', ' [이미지] ', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def clean_latex(latex: str) -> str:
    """LaTeX 수식 정제 - latex_cleaner 모듈 사용"""
    return latex_cleaner_clean(latex)


def normalize_image_path(path: str, item_id: str) -> str:
    """이미지 경로 정규화"""
    if not path:
        return ""

    # Windows 경로를 Unix로 변환
    path = path.replace('\\', '/')

    # 상대 경로로 정규화
    if not path.startswith(item_id):
        # 이미 정규화된 경우 그대로 반환
        pass

    return path


def verify_image_exists(image_path: str, data_dir: Path, source_file: str) -> bool:
    """이미지 파일 존재 여부 확인"""
    if not image_path:
        return False

    # source_file에서 날짜 폴더 추출
    source_path = Path(source_file)
    # data/YYYYMMDD/ID.iml 또는 data/YYYY/MM/DD/ID.iml 형태
    relative_source = source_path.relative_to(data_dir) if source_path.is_relative_to(data_dir) else source_path

    # 이미지 경로 구성
    parent_dir = source_path.parent
    full_path = parent_dir / image_path

    return full_path.exists()


def extract_keywords(kw_str: str) -> List[str]:
    """키워드 문자열에서 키워드 리스트 추출"""
    if not kw_str:
        return []

    # 일반적인 구분자로 분리
    keywords = re.split(r'[,;_\-\s]+', kw_str)

    # 빈 문자열 및 숫자만 있는 항목 제거
    keywords = [k.strip() for k in keywords if k.strip() and not k.strip().isdigit()]

    return keywords


def preprocess_item(item: Dict[str, Any], data_dir: Path) -> Dict[str, Any]:
    """단일 문항 전처리"""
    processed = {
        "id": item.get("id", ""),
        "metadata": {},
        "content": {},
        "images": {},
        "has_image": False,
        "validation": {
            "is_valid": True,
            "errors": []
        }
    }

    # 메타데이터 처리
    meta = item.get("metadata", {})
    processed["metadata"] = {
        "difficulty": meta.get("difficulty", ""),
        "difficulty_code": meta.get("difficulty_code", ""),
        "question_type": meta.get("question_type", ""),
        "question_type_code": meta.get("question_type_code", ""),
        "curriculum": meta.get("curriculum", ""),
        "school_level": meta.get("school_level", ""),
        "grade": meta.get("grade", ""),
        "subject": meta.get("subject", ""),
        "subject_detail": meta.get("subject_detail", ""),
        "semester": meta.get("semester", ""),
        "unit_large": meta.get("unit_large", ""),
        "unit_medium": meta.get("unit_medium", ""),
        "unit_small": meta.get("unit_small", ""),
        "keywords": extract_keywords(meta.get("keywords", "")),
        "keywords_raw": meta.get("keywords", ""),
        "year": meta.get("year"),
        "source": meta.get("source", ""),
        "exam_name": meta.get("exam_name", ""),
    }

    # 콘텐츠 처리
    content = item.get("content", {})

    # 문제 텍스트 정제
    question_text = clean_text(content.get("question", ""))
    processed["content"]["question"] = question_text

    # 문제 LaTeX
    question_latex = [clean_latex(l) for l in content.get("question_latex", []) if l]
    processed["content"]["question_latex"] = question_latex

    # 선택지 정제
    choices = [clean_text(c) for c in content.get("choices", [])]
    processed["content"]["choices"] = choices

    # 정답
    processed["content"]["answer"] = content.get("answer")
    processed["content"]["answers"] = content.get("answers", [])
    processed["content"]["answer_text"] = content.get("answer_text", "")

    # 해설 정제
    explanation_text = clean_text(content.get("explanation", ""))
    processed["content"]["explanation"] = explanation_text

    explanation_latex = [clean_latex(l) for l in content.get("explanation_latex", []) if l]
    processed["content"]["explanation_latex"] = explanation_latex

    # 이미지 처리
    source_file = item.get("source_file", "")
    question_images = content.get("question_images", [])
    explanation_images = content.get("explanation_images", [])

    # 이미지 경로 정규화 및 존재 확인
    processed["images"]["question"] = []
    processed["images"]["explanation"] = []
    processed["images"]["verified"] = []
    processed["images"]["missing"] = []

    for img_path in question_images:
        normalized = normalize_image_path(img_path, processed["id"])
        processed["images"]["question"].append(normalized)

        # 존재 확인
        if source_file:
            source_path = Path(source_file)
            if source_path.parts[0] == 'data':
                full_img_path = data_dir.parent / source_path.parent / normalized
            else:
                full_img_path = source_path.parent / normalized

            if full_img_path.exists():
                processed["images"]["verified"].append(normalized)
            else:
                processed["images"]["missing"].append(normalized)

    for img_path in explanation_images:
        normalized = normalize_image_path(img_path, processed["id"])
        processed["images"]["explanation"].append(normalized)

        if source_file:
            source_path = Path(source_file)
            if source_path.parts[0] == 'data':
                full_img_path = data_dir.parent / source_path.parent / normalized
            else:
                full_img_path = source_path.parent / normalized

            if full_img_path.exists():
                processed["images"]["verified"].append(normalized)
            else:
                processed["images"]["missing"].append(normalized)

    # 이미지 여부
    processed["has_image"] = bool(question_images or explanation_images)

    # 검증
    errors = []

    # 필수 필드 확인
    if not processed["id"]:
        errors.append("missing_id")

    if not question_text:
        errors.append("missing_question")

    # 선택형인데 선택지 없음
    if processed["metadata"]["question_type"] == "선택형" and len(choices) == 0:
        errors.append("missing_choices")

    # 정답 범위 확인 (선택형)
    if processed["metadata"]["question_type"] == "선택형":
        answer = processed["content"]["answer"]
        if answer is not None and (answer < 1 or answer > 5):
            errors.append("invalid_answer_range")

    # 누락된 이미지
    if processed["images"]["missing"]:
        errors.append("missing_images")

    processed["validation"]["errors"] = errors
    processed["validation"]["is_valid"] = len(errors) == 0

    # 소스 파일 (디버깅용)
    processed["_source_file"] = source_file

    return processed


def generate_statistics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """통계 생성"""
    stats = {
        "total": len(items),
        "valid": 0,
        "invalid": 0,
        "with_image": 0,
        "text_only": 0,
        "by_question_type": defaultdict(int),
        "by_difficulty": defaultdict(int),
        "by_grade": defaultdict(int),
        "by_semester": defaultdict(int),
        "by_unit_large": defaultdict(int),
        "validation_errors": defaultdict(int),
        "image_stats": {
            "total_images": 0,
            "verified": 0,
            "missing": 0
        }
    }

    for item in items:
        # 유효성
        if item["validation"]["is_valid"]:
            stats["valid"] += 1
        else:
            stats["invalid"] += 1
            for err in item["validation"]["errors"]:
                stats["validation_errors"][err] += 1

        # 이미지
        if item["has_image"]:
            stats["with_image"] += 1
        else:
            stats["text_only"] += 1

        # 분류
        meta = item["metadata"]
        stats["by_question_type"][meta.get("question_type", "unknown")] += 1
        stats["by_difficulty"][meta.get("difficulty", "unknown")] += 1
        stats["by_grade"][meta.get("grade", "unknown")] += 1
        stats["by_semester"][meta.get("semester", "unknown")] += 1
        stats["by_unit_large"][meta.get("unit_large", "unknown")] += 1

        # 이미지 통계
        imgs = item.get("images", {})
        stats["image_stats"]["total_images"] += len(imgs.get("question", [])) + len(imgs.get("explanation", []))
        stats["image_stats"]["verified"] += len(imgs.get("verified", []))
        stats["image_stats"]["missing"] += len(imgs.get("missing", []))

    # defaultdict를 일반 dict로 변환
    stats["by_question_type"] = dict(stats["by_question_type"])
    stats["by_difficulty"] = dict(stats["by_difficulty"])
    stats["by_grade"] = dict(stats["by_grade"])
    stats["by_semester"] = dict(stats["by_semester"])
    stats["by_unit_large"] = dict(stats["by_unit_large"])
    stats["validation_errors"] = dict(stats["validation_errors"])

    return stats


def main():
    print("=" * 60)
    print("Data Preprocessing")
    print("=" * 60)

    # Load parsed data
    print(f"\n[1/4] Loading parsed data from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get("items", [])
    print(f"      Loaded {len(items):,} items")

    # Preprocess
    print(f"\n[2/4] Preprocessing items...")
    processed_items = []

    total = len(items)
    for i, item in enumerate(items):
        if (i + 1) % 1000 == 0 or i == 0 or i == total - 1:
            print(f"      Processing: {i + 1:,}/{total:,} ({(i+1)/total*100:.1f}%)")

        processed = preprocess_item(item, DATA_DIR)
        processed_items.append(processed)

    print(f"      Preprocessed {len(processed_items):,} items")

    # Generate statistics
    print(f"\n[3/4] Generating statistics...")
    stats = generate_statistics(processed_items)

    # Save outputs
    print(f"\n[4/4] Saving outputs to {OUTPUT_DIR}...")

    # Final items JSON
    items_file = OUTPUT_DIR / "items.json"
    with open(items_file, 'w', encoding='utf-8') as f:
        json.dump({
            "total_items": len(processed_items),
            "valid_items": stats["valid"],
            "items": processed_items
        }, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {items_file}")

    # Statistics JSON
    stats_file = OUTPUT_DIR / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"      Saved: {stats_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("Preprocessing Summary")
    print("=" * 60)
    print(f"  Total items: {stats['total']:,}")
    print(f"  Valid items: {stats['valid']:,} ({stats['valid']/stats['total']*100:.1f}%)")
    print(f"  Invalid items: {stats['invalid']:,}")

    print(f"\n  By Image Presence:")
    print(f"    - With image: {stats['with_image']:,}")
    print(f"    - Text only: {stats['text_only']:,}")

    print(f"\n  Image Statistics:")
    print(f"    - Total images: {stats['image_stats']['total_images']:,}")
    print(f"    - Verified: {stats['image_stats']['verified']:,}")
    print(f"    - Missing: {stats['image_stats']['missing']:,}")

    print(f"\n  By Question Type:")
    for qt, count in sorted(stats["by_question_type"].items(), key=lambda x: -x[1]):
        print(f"    - {qt}: {count:,}")

    print(f"\n  By Difficulty:")
    for df, count in sorted(stats["by_difficulty"].items()):
        print(f"    - {df}: {count:,}")

    print(f"\n  By Semester:")
    for sem, count in sorted(stats["by_semester"].items()):
        print(f"    - {sem}: {count:,}")

    if stats["validation_errors"]:
        print(f"\n  Validation Errors:")
        for err, count in sorted(stats["validation_errors"].items(), key=lambda x: -x[1]):
            print(f"    - {err}: {count:,}")

    print("\n" + "=" * 60)
    print("Preprocessing completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
