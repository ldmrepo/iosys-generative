"""PDF 문항 추출 파이프라인

P1-LOAD: PDF 로드 및 이미지 변환
P2-SEGMENT: 문항/지문 경계 추출 (Agentic Vision)
P3-CROP: 문항/지문 이미지 크롭
P4-VISUALIZE: 세그멘테이션 결과 시각화
P5-VERIFY: 추출 검증
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .core.config import settings
from .core.schemas import (
    ExtractionResult, ExtractedItem, PageLayout, PassageInfo
)
from .agents.agentic_vision_client import AgenticVisionClient
from .extractors.pdf_extractor import PDFExtractor


class ItemExtractionPipeline:
    """문항 추출 파이프라인"""

    def __init__(self):
        """파이프라인 초기화"""
        self.vision_client = AgenticVisionClient()
        self.output_dir = settings.output_dir

    def run(
        self,
        pdf_path: Path,
        page_range: Optional[tuple[int, int]] = None,
        save_images: bool = True,
        crop_items: bool = False
    ) -> ExtractionResult:
        """파이프라인 실행

        Args:
            pdf_path: PDF 파일 경로
            page_range: 처리할 페이지 범위 (시작, 끝) - None이면 전체
            save_images: 시각화 이미지 저장 여부
            crop_items: 문항/지문 개별 이미지 크롭 여부

        Returns:
            추출 결과
        """
        pdf_path = Path(pdf_path)
        print(f"\n{'='*60}")
        print(f"PDF 문항 추출 시작: {pdf_path.name}")
        print(f"{'='*60}")

        all_items: list[ExtractedItem] = []
        all_passages: list[PassageInfo] = []
        all_layouts: list[PageLayout] = []

        with PDFExtractor(pdf_path) as extractor:
            total_pages = extractor.page_count

            # 페이지 범위 결정
            start_page = page_range[0] if page_range else 1
            end_page = page_range[1] if page_range else total_pages

            print(f"\n총 페이지: {total_pages}, 처리 범위: {start_page}-{end_page}")

            for page_num in range(start_page, end_page + 1):
                print(f"\n[P1-LOAD] 페이지 {page_num}/{end_page} 로드 중...")

                # P1: 페이지 이미지 변환
                page_image = extractor.get_page_image(page_num)
                width, height = extractor.get_page_size(page_num)
                print(f"  이미지 크기: {width}x{height} 픽셀")

                # P2: 문항 경계 추출 (Agentic Vision)
                print(f"\n[P2-SEGMENT] 문항 경계 추출 중 (Agentic Vision)...")
                try:
                    items, passages = self.vision_client.extract_items_from_page(
                        page_image, page_num, width, height
                    )
                    print(f"  발견된 문항: {len(items)}개")
                    if passages:
                        print(f"  공유 지문: {len(passages)}개")

                    for item in items:
                        ref_info = f" [→{item.passage_ref}]" if item.passage_ref else ""
                        print(f"    - 문항 {item.item_number}: "
                              f"({item.bbox.x1:.0f}, {item.bbox.y1:.0f}) - "
                              f"({item.bbox.x2:.0f}, {item.bbox.y2:.0f}){ref_info}")

                    for passage in passages:
                        bbox_count = len(passage.bbox_list) if passage.bbox_list else 1
                        print(f"    - 지문 [{passage.item_range}]: "
                              f"({passage.bbox.x1:.0f}, {passage.bbox.y1:.0f}) - "
                              f"({passage.bbox.x2:.0f}, {passage.bbox.y2:.0f})"
                              f" ({bbox_count}개 영역)")

                    all_items.extend(items)
                    all_passages.extend(passages)

                except Exception as e:
                    print(f"  문항 추출 실패: {e}")
                    import traceback
                    traceback.print_exc()

            # P3: 문항/지문 이미지 크롭
            if crop_items and all_items:
                print(f"\n[P3-CROP] 문항/지문 이미지 크롭 중...")
                items_dir = self.output_dir / "items" / pdf_path.stem
                extractor.save_all_items(all_items, items_dir)
                print(f"  문항 저장 위치: {items_dir}")

                if all_passages:
                    passages_dir = self.output_dir / "passages" / pdf_path.stem
                    extractor.save_all_passages(all_passages, passages_dir)
                    print(f"  지문 저장 위치: {passages_dir}")

            # P4: 세그멘테이션 결과 시각화
            if save_images and all_items:
                print(f"\n[P4-VISUALIZE] 세그멘테이션 결과 저장 중...")
                output_subdir = self.output_dir / "segmented" / pdf_path.stem
                extractor.save_all_pages_with_boxes(all_items, output_subdir, all_passages)
                print(f"  저장 위치: {output_subdir}")

            # P5: 검증
            print(f"\n[P5-VERIFY] 추출 검증...")
            print(f"  총 추출 문항: {len(all_items)}개")
            print(f"  총 공유 지문: {len(all_passages)}개")

        # 결과 생성
        result = ExtractionResult(
            source_pdf=str(pdf_path),
            total_pages=total_pages,
            processed_pages=end_page - start_page + 1,
            items=all_items,
            passages=all_passages,
            layouts=all_layouts,
            extracted_at=datetime.now(),
            model_version=settings.gemini_model
        )

        # Agentic 로그 출력
        self._print_agentic_summary()

        return result

    def _print_agentic_summary(self):
        """Agentic Vision 실행 요약 출력"""
        logs = self.vision_client.get_logs()
        if not logs:
            return

        print(f"\n{'='*60}")
        print("Agentic Vision 실행 요약")
        print(f"{'='*60}")

        total_iterations = sum(log.total_iterations for log in logs)
        total_steps = sum(len(log.steps) for log in logs)

        print(f"총 페이지: {len(logs)}")
        print(f"총 코드 실행: {total_iterations}회")
        print(f"총 단계: {total_steps}")

        # 각 페이지별 상세
        for log in logs:
            print(f"\n페이지 {log.page_number}:")
            think_count = sum(1 for s in log.steps if s.step_type == "think")
            act_count = sum(1 for s in log.steps if s.step_type == "act")
            observe_count = sum(1 for s in log.steps if s.step_type == "observe")
            print(f"  Think: {think_count}, Act: {act_count}, Observe: {observe_count}")

    def save_result(self, result: ExtractionResult, output_path: Optional[Path] = None) -> Path:
        """결과 저장

        Args:
            result: 추출 결과
            output_path: 출력 경로 (선택)

        Returns:
            저장된 파일 경로
        """
        if output_path is None:
            pdf_name = Path(result.source_pdf).stem
            output_path = self.output_dir / f"{pdf_name}_extraction.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))

        print(f"\n결과 저장: {output_path}")
        return output_path
