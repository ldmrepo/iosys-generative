#!/usr/bin/env python3
"""
이미지 데이터 유효성 검증
- 폴더 구조 분석 (YYYYMMDD vs YYYY/MM/DD)
- has_image 플래그와 실제 이미지 매칭 확인
- 손상된 이미지 파일 검출
- 매칭률 통계
"""

import json
from pathlib import Path
from PIL import Image
from collections import defaultdict
from tqdm import tqdm

# 경로 설정
BASE_DIR = Path("/root/work/mcp/iosys-generative")
IMAGE_DIR = BASE_DIR / "data/raw"
ITEMS_FILE = BASE_DIR / "poc/data/items_full.json"

# 대체 경로 (Vast.ai용)
ALT_IMAGE_DIR = Path("./images")
ALT_ITEMS_FILE = Path("./items_full.json")


def find_image_path(item_id, image_dir):
    """문항 ID에 해당하는 이미지 경로 찾기 (두 가지 구조 지원)"""
    if not image_dir.exists():
        return None

    def check_item_dir(item_path):
        if not item_path.exists():
            return None
        draw_path = item_path / "DrawObjPic"
        if draw_path.exists():
            for img_file in draw_path.glob("*.png"):
                return str(img_file)
            for img_file in draw_path.glob("*.jpg"):
                return str(img_file)
        for img_file in item_path.glob("*.png"):
            return str(img_file)
        for img_file in item_path.glob("*.jpg"):
            return str(img_file)
        return None

    # 패턴 1: YYYYMMDD/item_id/
    for date_dir in image_dir.iterdir():
        if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
            result = check_item_dir(date_dir / item_id)
            if result:
                return result

    # 패턴 2: YYYY/MM/DD/item_id/
    for year_dir in image_dir.iterdir():
        if year_dir.is_dir() and year_dir.name.isdigit() and len(year_dir.name) == 4:
            for month_dir in year_dir.iterdir():
                if month_dir.is_dir():
                    for day_dir in month_dir.iterdir():
                        if day_dir.is_dir():
                            result = check_item_dir(day_dir / item_id)
                            if result:
                                return result

    return None


def check_image_readable(image_path):
    """이미지 파일이 정상적으로 읽히는지 확인"""
    try:
        with Image.open(image_path) as img:
            img.verify()
        return True, None
    except Exception as e:
        return False, str(e)


def analyze_folder_structure(image_dir):
    """이미지 폴더 구조 분석"""
    print(f"\n{'='*60}")
    print("1. 폴더 구조 분석")
    print(f"{'='*60}")

    structure = {
        "YYYYMMDD": [],  # 8자리 날짜 폴더
        "YYYY": [],      # 4자리 년도 폴더
        "other": []
    }

    for item in image_dir.iterdir():
        if item.is_dir():
            if item.name.isdigit():
                if len(item.name) == 8:
                    structure["YYYYMMDD"].append(item.name)
                elif len(item.name) == 4:
                    structure["YYYY"].append(item.name)
                else:
                    structure["other"].append(item.name)
            else:
                structure["other"].append(item.name)

    print(f"  YYYYMMDD 형식 폴더: {len(structure['YYYYMMDD'])}개")
    if structure["YYYYMMDD"]:
        print(f"    예시: {structure['YYYYMMDD'][:3]}")

    print(f"  YYYY 형식 폴더: {len(structure['YYYY'])}개")
    if structure["YYYY"]:
        print(f"    예시: {structure['YYYY'][:3]}")
        # YYYY/MM/DD 구조 확인
        for year in structure["YYYY"][:1]:
            year_path = image_dir / year
            months = [m.name for m in year_path.iterdir() if m.is_dir()]
            print(f"    {year}/ 하위: {months[:3]}...")

    if structure["other"]:
        print(f"  기타 폴더: {len(structure['other'])}개")
        print(f"    예시: {structure['other'][:3]}")

    return structure


def count_images_by_structure(image_dir):
    """구조별 이미지 수 카운트"""
    print(f"\n{'='*60}")
    print("2. 구조별 이미지 수")
    print(f"{'='*60}")

    yyyymmdd_count = 0
    yyyy_mm_dd_count = 0

    # YYYYMMDD 구조
    for date_dir in image_dir.iterdir():
        if date_dir.is_dir() and date_dir.name.isdigit() and len(date_dir.name) == 8:
            yyyymmdd_count += sum(1 for _ in date_dir.rglob("*.png"))
            yyyymmdd_count += sum(1 for _ in date_dir.rglob("*.jpg"))

    # YYYY/MM/DD 구조
    for year_dir in image_dir.iterdir():
        if year_dir.is_dir() and year_dir.name.isdigit() and len(year_dir.name) == 4:
            yyyy_mm_dd_count += sum(1 for _ in year_dir.rglob("*.png"))
            yyyy_mm_dd_count += sum(1 for _ in year_dir.rglob("*.jpg"))

    print(f"  YYYYMMDD 구조 이미지: {yyyymmdd_count:,}개")
    print(f"  YYYY/MM/DD 구조 이미지: {yyyy_mm_dd_count:,}개")
    print(f"  총 이미지: {yyyymmdd_count + yyyy_mm_dd_count:,}개")

    return {"YYYYMMDD": yyyymmdd_count, "YYYY/MM/DD": yyyy_mm_dd_count}


def validate_has_image_matching(items, image_dir):
    """has_image 플래그와 실제 이미지 매칭 검증"""
    print(f"\n{'='*60}")
    print("3. has_image 플래그 매칭 검증")
    print(f"{'='*60}")

    has_image_items = [i for i in items if i.get("has_image")]
    print(f"  has_image=True 문항 수: {len(has_image_items):,}개")

    matched = 0
    not_matched = []
    matched_by_structure = {"YYYYMMDD": 0, "YYYY/MM/DD": 0}

    for item in tqdm(has_image_items, desc="  매칭 검증"):
        path = find_image_path(item["id"], image_dir)
        if path:
            matched += 1
            if "/20" in path and len(path.split("/20")[1].split("/")[0]) == 6:
                # YYYYMMDD 형식
                matched_by_structure["YYYYMMDD"] += 1
            else:
                matched_by_structure["YYYY/MM/DD"] += 1
        else:
            not_matched.append(item["id"])

    match_rate = matched / len(has_image_items) * 100 if has_image_items else 0

    print(f"\n  매칭 결과:")
    print(f"    성공: {matched:,}개 ({match_rate:.1f}%)")
    print(f"    실패: {len(not_matched):,}개")
    print(f"    YYYYMMDD 구조: {matched_by_structure['YYYYMMDD']:,}개")
    print(f"    YYYY/MM/DD 구조: {matched_by_structure['YYYY/MM/DD']:,}개")

    if not_matched:
        print(f"\n  미매칭 ID 샘플 (최대 10개):")
        for item_id in not_matched[:10]:
            print(f"    - {item_id}")

    return {
        "total": len(has_image_items),
        "matched": matched,
        "not_matched": not_matched,
        "match_rate": match_rate
    }


def check_corrupted_images(items, image_dir, sample_size=500):
    """손상된 이미지 검출"""
    print(f"\n{'='*60}")
    print(f"4. 이미지 파일 무결성 검사 (샘플 {sample_size}개)")
    print(f"{'='*60}")

    has_image_items = [i for i in items if i.get("has_image")]

    # 샘플링
    import random
    sample_items = random.sample(has_image_items, min(sample_size, len(has_image_items)))

    valid = 0
    corrupted = []
    not_found = 0
    by_extension = defaultdict(lambda: {"valid": 0, "corrupted": 0})

    for item in tqdm(sample_items, desc="  무결성 검사"):
        path = find_image_path(item["id"], image_dir)
        if not path:
            not_found += 1
            continue

        ext = Path(path).suffix.lower()
        is_valid, error = check_image_readable(path)

        if is_valid:
            valid += 1
            by_extension[ext]["valid"] += 1
        else:
            corrupted.append({"id": item["id"], "path": path, "error": error})
            by_extension[ext]["corrupted"] += 1

    checked = valid + len(corrupted)
    valid_rate = valid / checked * 100 if checked else 0

    print(f"\n  검사 결과:")
    print(f"    검사된 파일: {checked:,}개")
    print(f"    정상: {valid:,}개 ({valid_rate:.1f}%)")
    print(f"    손상: {len(corrupted):,}개")
    print(f"    이미지 없음: {not_found:,}개")

    print(f"\n  확장자별 결과:")
    for ext, counts in by_extension.items():
        total = counts["valid"] + counts["corrupted"]
        print(f"    {ext}: {counts['valid']}/{total} 정상")

    if corrupted:
        print(f"\n  손상된 파일 (최대 10개):")
        for c in corrupted[:10]:
            print(f"    - {c['path']}")
            print(f"      에러: {c['error'][:50]}...")

    return {
        "checked": checked,
        "valid": valid,
        "corrupted": corrupted,
        "valid_rate": valid_rate
    }


def main():
    print("=" * 60)
    print("  이미지 데이터 유효성 검증")
    print("=" * 60)

    # 경로 확인
    image_dir = IMAGE_DIR if IMAGE_DIR.exists() else ALT_IMAGE_DIR
    items_file = ITEMS_FILE if ITEMS_FILE.exists() else ALT_ITEMS_FILE

    print(f"\n이미지 디렉토리: {image_dir}")
    print(f"데이터 파일: {items_file}")

    if not image_dir.exists():
        print(f"\n❌ 이미지 디렉토리를 찾을 수 없습니다: {image_dir}")
        print("   IMAGE_DIR 경로를 수정해주세요.")
        return

    if not items_file.exists():
        print(f"\n❌ 데이터 파일을 찾을 수 없습니다: {items_file}")
        print("   ITEMS_FILE 경로를 수정해주세요.")
        return

    # 데이터 로드
    print("\n데이터 로드 중...")
    with open(items_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data["items"] if "items" in data else data
    print(f"총 문항 수: {len(items):,}개")

    # 1. 폴더 구조 분석
    analyze_folder_structure(image_dir)

    # 2. 구조별 이미지 수
    count_images_by_structure(image_dir)

    # 3. has_image 매칭 검증
    matching_result = validate_has_image_matching(items, image_dir)

    # 4. 손상된 이미지 검출
    corruption_result = check_corrupted_images(items, image_dir)

    # 최종 요약
    print(f"\n{'='*60}")
    print("  검증 결과 요약")
    print(f"{'='*60}")
    print(f"  has_image 매칭률: {matching_result['match_rate']:.1f}%")
    print(f"    ({matching_result['matched']:,}/{matching_result['total']:,})")
    print(f"  이미지 무결성: {corruption_result['valid_rate']:.1f}%")
    print(f"    ({corruption_result['valid']:,}/{corruption_result['checked']:,})")

    if matching_result['match_rate'] >= 99 and corruption_result['valid_rate'] >= 99:
        print(f"\n  ✅ 데이터 검증 통과")
    else:
        print(f"\n  ⚠️  데이터 검증 문제 발견")
        if matching_result['match_rate'] < 99:
            print(f"     - has_image 매칭률이 낮습니다")
        if corruption_result['valid_rate'] < 99:
            print(f"     - 손상된 이미지가 있습니다")

    print("=" * 60)


if __name__ == "__main__":
    main()
