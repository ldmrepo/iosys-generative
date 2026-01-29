#!/usr/bin/env python3
"""
이미지 데이터 유효성 검증
- 18개 파트 파일 로드 지원
- 폴더 구조 분석 (YYYYMMDD vs YYYY/MM/DD)
- has_image 플래그와 실제 이미지 매칭 확인
- 손상된 이미지 파일 검출
- 매칭률 통계
- JSON 결과 출력
"""

import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# 경로 설정 (로컬/Vast.ai 자동 감지)
def get_paths():
    """환경에 맞는 경로 반환"""
    # 로컬 환경
    local_base = Path("/root/work/mcp/iosys-generative")
    if local_base.exists():
        return {
            "image_dir": local_base / "data/raw",
            "items_dir": local_base / "data/processed",
            "output_dir": local_base / "poc/results"
        }

    # Vast.ai 환경 (홈 디렉토리 기준)
    home = Path.home()
    return {
        "image_dir": home / "data/raw",
        "items_dir": home / "data/processed",
        "output_dir": home / "poc/results"
    }


def load_all_items(items_dir):
    """18개 파트 파일에서 모든 문항 로드"""
    all_items = []
    for i in range(1, 19):
        file_path = items_dir / f"items_part{i:02d}.json"
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                items = data.get("items", data)
                all_items.extend(items)
                print(f"  Part {i:02d}: {len(items):,} items")
        else:
            print(f"  Part {i:02d}: 파일 없음")
    return all_items


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


def analyze_folder_structure(image_dir):
    """이미지 폴더 구조 분석"""
    print(f"\n{'='*60}")
    print("1. 폴더 구조 분석")
    print(f"{'='*60}")

    structure = {
        "YYYYMMDD": [],
        "YYYY": [],
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
    print(f"  YYYY 형식 폴더: {len(structure['YYYY'])}개")

    return structure


def count_images(image_dir):
    """이미지 파일 수 카운트"""
    print(f"\n{'='*60}")
    print("2. 이미지 파일 수")
    print(f"{'='*60}")

    png_count = sum(1 for _ in image_dir.rglob("*.png"))
    jpg_count = sum(1 for _ in image_dir.rglob("*.jpg"))

    print(f"  PNG 파일: {png_count:,}개")
    print(f"  JPG 파일: {jpg_count:,}개")
    print(f"  총 이미지: {png_count + jpg_count:,}개")

    return {"png": png_count, "jpg": jpg_count, "total": png_count + jpg_count}


def validate_matching(items, image_dir):
    """has_image 플래그와 실제 이미지 매칭 검증"""
    print(f"\n{'='*60}")
    print("3. has_image 매칭 검증")
    print(f"{'='*60}")

    has_image_items = [i for i in items if i.get("has_image")]
    print(f"  has_image=True 문항: {len(has_image_items):,}개")

    matched = 0
    not_matched_ids = []
    by_subject = defaultdict(lambda: {"matched": 0, "not_matched": 0})

    for i, item in enumerate(has_image_items):
        meta = item.get("metadata", {})
        subject = meta.get("subject", "unknown")

        path = find_image_path(item["id"], image_dir)
        if path:
            matched += 1
            by_subject[subject]["matched"] += 1
        else:
            not_matched_ids.append(item["id"])
            by_subject[subject]["not_matched"] += 1

        if (i + 1) % 10000 == 0:
            print(f"  진행: {i+1:,}/{len(has_image_items):,}")

    match_rate = matched / len(has_image_items) * 100 if has_image_items else 0

    print(f"\n  매칭 결과:")
    print(f"    성공: {matched:,}개 ({match_rate:.1f}%)")
    print(f"    실패: {len(not_matched_ids):,}개")

    print(f"\n  과목별 매칭 실패:")
    for subj, counts in sorted(by_subject.items(), key=lambda x: -x[1]["not_matched"])[:5]:
        if counts["not_matched"] > 0:
            total = counts["matched"] + counts["not_matched"]
            rate = counts["matched"] / total * 100
            print(f"    {subj}: {counts['not_matched']:,}개 실패 ({rate:.1f}% 매칭)")

    return {
        "total_has_image": len(has_image_items),
        "matched": matched,
        "not_matched": len(not_matched_ids),
        "match_rate": match_rate,
        "not_matched_ids": not_matched_ids[:100],  # 샘플만 저장
        "by_subject": {k: dict(v) for k, v in by_subject.items()}
    }


def main():
    print("=" * 60)
    print("  이미지 데이터 유효성 검증 (176,443 items)")
    print("=" * 60)

    # 경로 설정
    paths = get_paths()
    image_dir = paths["image_dir"]
    items_dir = paths["items_dir"]
    output_dir = paths["output_dir"]

    print(f"\n이미지 디렉토리: {image_dir}")
    print(f"문항 디렉토리: {items_dir}")

    if not image_dir.exists():
        print(f"\n❌ 이미지 디렉토리를 찾을 수 없습니다: {image_dir}")
        return

    if not items_dir.exists():
        print(f"\n❌ 문항 디렉토리를 찾을 수 없습니다: {items_dir}")
        return

    # 데이터 로드
    print("\n[1/4] 데이터 로드...")
    items = load_all_items(items_dir)
    print(f"  총 문항: {len(items):,}개")

    # 폴더 구조 분석
    structure = analyze_folder_structure(image_dir)

    # 이미지 수 카운트
    image_counts = count_images(image_dir)

    # 매칭 검증
    matching_result = validate_matching(items, image_dir)

    # 결과 요약
    print(f"\n{'='*60}")
    print("  검증 결과 요약")
    print(f"{'='*60}")
    print(f"  총 문항: {len(items):,}개")
    print(f"  has_image 문항: {matching_result['total_has_image']:,}개")
    print(f"  이미지 매칭: {matching_result['matched']:,}개 ({matching_result['match_rate']:.1f}%)")
    print(f"  총 이미지 파일: {image_counts['total']:,}개")

    if matching_result['match_rate'] >= 90:
        print(f"\n  ✅ 검증 통과 (90% 이상 매칭)")
    else:
        print(f"\n  ⚠️  매칭률 부족")

    # JSON 결과 저장
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "timestamp": datetime.now().isoformat(),
        "paths": {
            "image_dir": str(image_dir),
            "items_dir": str(items_dir)
        },
        "summary": {
            "total_items": len(items),
            "has_image_items": matching_result["total_has_image"],
            "matched": matching_result["matched"],
            "not_matched": matching_result["not_matched"],
            "match_rate": matching_result["match_rate"],
            "total_images": image_counts["total"]
        },
        "folder_structure": {
            "YYYYMMDD_folders": len(structure["YYYYMMDD"]),
            "YYYY_folders": len(structure["YYYY"])
        },
        "by_subject": matching_result["by_subject"]
    }

    output_file = output_dir / "validation_result.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_file}")

    print("=" * 60)


if __name__ == "__main__":
    main()
