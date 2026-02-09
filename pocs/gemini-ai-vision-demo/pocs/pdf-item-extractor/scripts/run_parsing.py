#!/usr/bin/env python3
"""문항 콘텐츠 파싱 스크립트

크롭된 문항 이미지에서 구조화된 콘텐츠를 추출합니다.

사용법:
    python scripts/run_parsing.py [OPTIONS]

옵션:
    --input, -i     추출 결과 JSON 파일 경로
    --items-dir     문항 이미지 디렉토리 (선택)
    --output, -o    파싱 결과 출력 경로
"""

import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.core.schemas import ExtractedItem
from src.parsers.item_parser import ItemParser
from src.parsers.html_report import HTMLReportGenerator
from src.parsers.content_visualizer import ContentVisualizer


def main():
    parser = argparse.ArgumentParser(
        description="문항 콘텐츠 파싱 (P6-PARSE)"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="추출 결과 JSON 파일 경로"
    )
    parser.add_argument(
        "--items-dir",
        type=str,
        default=None,
        help="문항 이미지 디렉토리 (기본: JSON 내 경로 사용)"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="파싱 결과 출력 경로"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="파싱할 문항 수 제한 (테스트용)"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="HTML 비교 리포트 생성"
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="콘텐츠 블록 bbox 시각화 이미지 생성"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("P6-PARSE: 문항 콘텐츠 파싱")
    print("=" * 60)

    # 추출 결과 로드
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"파일을 찾을 수 없습니다: {input_path}")
        return

    with open(input_path, "r", encoding="utf-8") as f:
        extraction_data = json.load(f)

    # ExtractedItem 목록 생성
    items = []
    for item_data in extraction_data.get("items", []):
        item = ExtractedItem(**item_data)

        # items-dir 옵션으로 경로 재지정
        if args.items_dir and item.image_path:
            image_name = Path(item.image_path).name
            item.image_path = str(Path(args.items_dir) / image_name)

        items.append(item)

    print(f"\n[입력]")
    print(f"  추출 결과: {input_path.name}")
    print(f"  총 문항 수: {len(items)}개")

    # 제한 적용
    if args.limit:
        items = items[:args.limit]
        print(f"  파싱 대상: {len(items)}개 (제한 적용)")

    # 파서 초기화
    item_parser = ItemParser()

    print(f"\n[P6-PARSE] 문항 콘텐츠 파싱 중...")
    parsed_items = item_parser.parse_items(items)

    print(f"\n[결과]")
    print(f"  파싱 완료: {len(parsed_items)}개")

    # 통계
    total_text = sum(
        sum(1 for b in p.question if b.type.value == "text")
        for p in parsed_items
    )
    total_math = sum(
        sum(1 for b in p.question if b.type.value == "math")
        for p in parsed_items
    )
    total_image = sum(
        sum(1 for b in p.question if b.type.value == "image")
        for p in parsed_items
    )

    print(f"  총 텍스트 블록: {total_text}개")
    print(f"  총 수식 블록: {total_math}개")
    print(f"  총 이미지 블록: {total_image}개")

    # 결과 저장
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_parsed.json"

    item_parser.save_parsed_items(parsed_items, output_path)
    print(f"\n파싱 결과 저장: {output_path}")

    # HTML 리포트 생성
    if args.html:
        html_path = output_path.with_suffix(".html")
        pdf_name = Path(extraction_data.get("source_pdf", "")).stem
        title = f"문항 파싱 결과: {pdf_name}"

        report_generator = HTMLReportGenerator()
        report_generator.generate(parsed_items, html_path, title)
        print(f"HTML 리포트 저장: {html_path}")

    # 콘텐츠 블록 시각화
    if args.visualize:
        print(f"\n[P6-VISUALIZE] 콘텐츠 블록 시각화 중...")
        visualize_dir = input_path.parent / "visualized" / input_path.stem.replace("_extraction", "")

        visualizer = ContentVisualizer()
        visualizer.visualize_items(parsed_items, visualize_dir)
        print(f"시각화 이미지 저장: {visualize_dir}")


if __name__ == "__main__":
    main()
