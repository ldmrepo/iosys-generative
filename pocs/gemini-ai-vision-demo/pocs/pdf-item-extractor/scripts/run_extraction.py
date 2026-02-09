#!/usr/bin/env python3
"""PDF 문항 추출 POC 실행 스크립트

Agentic Vision을 사용하여 PDF에서 문항을 추출합니다.

사용법:
    python scripts/run_extraction.py [OPTIONS]

옵션:
    --pdf, -p       처리할 PDF 파일 경로 (기본: 수학-g10)
    --pages         처리할 페이지 범위 (예: 1-3)
    --crop          문항/지문 개별 이미지 크롭
    --no-save       시각화 이미지 저장 안함
    --force         기존 결과 무시하고 재실행
"""

import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import settings
from src.pipeline import ItemExtractionPipeline


def main():
    parser = argparse.ArgumentParser(
        description="Agentic Vision 기반 PDF 문항 추출 POC"
    )
    parser.add_argument(
        "--pdf", "-p",
        type=str,
        default=None,
        help="처리할 PDF 파일 경로"
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="처리할 페이지 범위 (예: 1-3)"
    )
    parser.add_argument(
        "--crop",
        action="store_true",
        help="문항/지문 개별 이미지 크롭"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="시각화 이미지 저장 안함"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        help="PDF 렌더링 DPI (기본: 100)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 결과 무시하고 재실행"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Agentic Vision PDF 문항 추출 POC")
    print("=" * 60)

    # DPI 설정 (CLI 옵션 우선)
    if args.dpi:
        settings.pdf_dpi = args.dpi

    # 모델 정보
    print(f"\n[사용 모델]")
    print(f"  Agentic Vision: {settings.gemini_model}")
    print(f"  PDF DPI: {settings.pdf_dpi}")

    # PDF 파일 결정
    if args.pdf:
        pdf_path = Path(args.pdf)
    else:
        # 기본값: 수학-g10 (가장 작은 파일)
        datas_dir = project_root.parent / "datas"
        pdf_path = datas_dir / "ebsi-2025-exam-math-수학-g10-202511.pdf"

    if not pdf_path.exists():
        print(f"\nPDF 파일을 찾을 수 없습니다: {pdf_path}")
        print(f"\n사용 가능한 PDF 목록:")
        datas_dir = project_root.parent / "datas"
        if datas_dir.exists():
            for f in sorted(datas_dir.glob("*.pdf")):
                print(f"  {f.name}")
        return

    print(f"\n[입력 PDF]")
    print(f"  파일: {pdf_path.name}")
    print(f"  크기: {pdf_path.stat().st_size / 1024:.1f} KB")

    # 페이지 범위 파싱
    page_range = None
    if args.pages:
        try:
            parts = args.pages.split("-")
            if len(parts) == 2:
                page_range = (int(parts[0]), int(parts[1]))
            elif len(parts) == 1:
                page_range = (int(parts[0]), int(parts[0]))
        except ValueError:
            print(f"잘못된 페이지 범위: {args.pages}")
            return

    if page_range:
        print(f"  페이지 범위: {page_range[0]}-{page_range[1]}")

    # 기존 결과 확인
    output_dir = settings.output_dir
    result_json_path = output_dir / f"{pdf_path.stem}_extraction.json"

    if result_json_path.exists() and not args.force:
        print(f"\n[캐시 발견] 기존 추출 결과 사용")
        print(f"  파일: {result_json_path.name}")
        print(f"  (재실행하려면 --force 옵션 사용)")

        # 기존 결과 로드
        with open(result_json_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)

        from src.core.schemas import ExtractionResult
        result = ExtractionResult(**cached_data)

        # 크롭만 필요한 경우 처리
        if args.crop:
            items_dir = output_dir / "items" / pdf_path.stem
            if items_dir.exists() and any(items_dir.glob("*.png")):
                print(f"  크롭 이미지 이미 존재: {items_dir}")
            else:
                print(f"\n[P3-CROP] 문항 이미지 크롭 중...")
                from src.extractors.pdf_extractor import PDFExtractor
                with PDFExtractor(pdf_path) as extractor:
                    extractor.save_all_items(result.items, items_dir)
                    if result.passages:
                        passages_dir = output_dir / "passages" / pdf_path.stem
                        extractor.save_all_passages(result.passages, passages_dir)

    else:
        # 파이프라인 실행
        pipeline = ItemExtractionPipeline()

        try:
            result = pipeline.run(
                pdf_path=pdf_path,
                page_range=page_range,
                save_images=not args.no_save,
                crop_items=args.crop
            )

            # 결과 저장
            pipeline.save_result(result)

        except Exception as e:
            print(f"\n오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return

    # 요약 출력
    print("\n" + "=" * 60)
    print("추출 결과 요약")
    print("=" * 60)
    print(f"처리된 페이지: {result.processed_pages}개")
    print(f"추출된 문항: {len(result.items)}개")
    print(f"공유 지문: {len(result.passages)}개")

    if result.items:
        print(f"\n[추출된 문항 목록]")
        for item in result.items:
            print(f"  문항 {item.item_number} (p{item.page_number}): "
                  f"{item.item_type.value}")
            if item.image_path:
                print(f"    이미지: {Path(item.image_path).name}")


if __name__ == "__main__":
    main()
