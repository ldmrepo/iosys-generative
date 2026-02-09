"""PDF 추출기

PyMuPDF를 사용하여 PDF를 이미지로 변환하고 문항을 crop합니다.
"""

import io
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

from ..core.config import settings
from ..core.schemas import BoundingBox, ExtractedItem, PassageInfo


class PDFExtractor:
    """PDF 추출기"""

    def __init__(self, pdf_path: Path, dpi: int = None):
        """PDF 추출기 초기화

        Args:
            pdf_path: PDF 파일 경로
            dpi: 렌더링 DPI (기본값: 설정에서 로드)
        """
        self.pdf_path = Path(pdf_path)
        self.dpi = dpi or settings.pdf_dpi
        self.doc = fitz.open(str(self.pdf_path))
        self._page_images: dict[int, bytes] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        """문서 닫기"""
        if self.doc:
            self.doc.close()

    @property
    def page_count(self) -> int:
        """총 페이지 수"""
        return len(self.doc)

    def get_page_image(self, page_number: int, force_reload: bool = False) -> bytes:
        """페이지를 이미지로 변환

        Args:
            page_number: 페이지 번호 (1부터 시작)
            force_reload: 캐시 무시하고 재생성

        Returns:
            PNG 이미지 바이트
        """
        if not force_reload and page_number in self._page_images:
            return self._page_images[page_number]

        # 페이지 인덱스 (0부터 시작)
        page_idx = page_number - 1
        if page_idx < 0 or page_idx >= len(self.doc):
            raise ValueError(f"유효하지 않은 페이지 번호: {page_number}")

        page = self.doc[page_idx]

        # DPI에 따른 변환 행렬
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        # 페이지를 픽스맵으로 렌더링
        pix = page.get_pixmap(matrix=mat)

        # PNG 바이트로 변환
        img_bytes = pix.tobytes("png")

        # 캐시에 저장
        self._page_images[page_number] = img_bytes

        return img_bytes

    def get_page_size(self, page_number: int) -> tuple[int, int]:
        """페이지 크기 반환 (렌더링 후 픽셀)

        Args:
            page_number: 페이지 번호

        Returns:
            (width, height) 픽셀
        """
        page_idx = page_number - 1
        page = self.doc[page_idx]

        zoom = self.dpi / 72.0
        width = int(page.rect.width * zoom)
        height = int(page.rect.height * zoom)

        return width, height

    def crop_region(
        self,
        page_number: int,
        bbox: BoundingBox,
        padding: int = 5
    ) -> bytes:
        """페이지에서 특정 영역 crop

        Args:
            page_number: 페이지 번호
            bbox: 바운딩 박스
            padding: 여백 (픽셀)

        Returns:
            크롭된 PNG 이미지 바이트
        """
        # 페이지 이미지 로드
        page_img_bytes = self.get_page_image(page_number)

        # PIL 이미지로 변환
        img = Image.open(io.BytesIO(page_img_bytes))

        # 여백 적용 및 경계 조정
        x1 = max(0, int(bbox.x1) - padding)
        y1 = max(0, int(bbox.y1) - padding)
        x2 = min(img.width, int(bbox.x2) + padding)
        y2 = min(img.height, int(bbox.y2) + padding)

        # 크롭
        cropped = img.crop((x1, y1, x2, y2))

        # PNG 바이트로 변환
        buffer = io.BytesIO()
        cropped.save(buffer, format="PNG")
        return buffer.getvalue()

    def save_item_image(
        self,
        item: ExtractedItem,
        output_dir: Path,
        padding: int = 10
    ) -> Path:
        """문항 이미지 저장

        Args:
            item: 추출된 문항
            output_dir: 출력 디렉토리
            padding: 여백 (픽셀)

        Returns:
            저장된 파일 경로
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 이미지 크롭
        img_bytes = self.crop_region(item.page_number, item.bbox, padding)

        # 파일명 생성
        filename = f"item_{item.item_number}_p{item.page_number}.png"
        output_path = output_dir / filename

        # 저장
        with open(output_path, "wb") as f:
            f.write(img_bytes)

        return output_path

    def save_all_items(
        self,
        items: list[ExtractedItem],
        output_dir: Path,
        padding: int = 10
    ) -> list[Path]:
        """모든 문항 이미지 저장

        Args:
            items: 추출된 문항 목록
            output_dir: 출력 디렉토리
            padding: 여백 (픽셀)

        Returns:
            저장된 파일 경로 목록
        """
        saved_paths = []
        for item in items:
            path = self.save_item_image(item, output_dir, padding)
            item.image_path = str(path)
            saved_paths.append(path)
            print(f"  문항 {item.item_number}: {path.name}")

        return saved_paths

    def save_passage_image(
        self,
        passage: PassageInfo,
        output_dir: Path,
        padding: int = 10
    ) -> list[Path]:
        """지문 이미지 저장 (다중 bbox 지원)

        Args:
            passage: 지문 정보
            output_dir: 출력 디렉토리
            padding: 여백 (픽셀)

        Returns:
            저장된 파일 경로 목록
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = []

        # bbox_list가 있으면 각각 저장, 없으면 메인 bbox만 저장
        bboxes = passage.bbox_list if passage.bbox_list else [passage.bbox]

        for idx, bbox in enumerate(bboxes):
            # 이미지 크롭
            img_bytes = self.crop_region(passage.page_number, bbox, padding)

            # 파일명 생성 (다중 bbox면 _1, _2 등 suffix 추가)
            if len(bboxes) > 1:
                filename = f"passage_{passage.passage_id}_p{passage.page_number}_{idx + 1}.png"
            else:
                filename = f"passage_{passage.passage_id}_p{passage.page_number}.png"
            output_path = output_dir / filename

            # 저장
            with open(output_path, "wb") as f:
                f.write(img_bytes)

            saved_paths.append(output_path)

        return saved_paths

    def save_all_passages(
        self,
        passages: list[PassageInfo],
        output_dir: Path,
        padding: int = 10
    ) -> list[Path]:
        """모든 지문 이미지 저장

        Args:
            passages: 지문 목록
            output_dir: 출력 디렉토리
            padding: 여백 (픽셀)

        Returns:
            저장된 파일 경로 목록
        """
        saved_paths = []
        for passage in passages:
            paths = self.save_passage_image(passage, output_dir, padding)
            # 첫 번째 경로를 대표 이미지로 저장
            passage.image_path = str(paths[0]) if paths else None
            saved_paths.extend(paths)

            # 저장 결과 출력
            if len(paths) > 1:
                print(f"  지문 [{passage.item_range}]: {len(paths)}개 영역")
                for p in paths:
                    print(f"    - {p.name}")
            else:
                print(f"  지문 [{passage.item_range}]: {paths[0].name}")

        return saved_paths

    def save_page_with_boxes(
        self,
        page_number: int,
        items: list[ExtractedItem],
        output_dir: Path,
        passages: list[PassageInfo] = None
    ) -> Path:
        """페이지 이미지에 bbox를 표시하여 저장

        Args:
            page_number: 페이지 번호
            items: 해당 페이지의 문항 목록
            output_dir: 출력 디렉토리
            passages: 해당 페이지의 지문 목록

        Returns:
            저장된 파일 경로
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 페이지 이미지 로드
        page_img_bytes = self.get_page_image(page_number)
        img = Image.open(io.BytesIO(page_img_bytes)).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 색상 팔레트 - 문항용
        item_colors = ["#FF0000", "#00FF00", "#0000FF", "#FF00FF", "#00FFFF", "#FFFF00"]
        # 지문용 색상 (주황색 계열)
        passage_color = "#FFA500"

        # 지문 bbox 그리기 (반투명 배경)
        if passages:
            for passage in passages:
                # 모든 bbox 그리기 (단 넘김 시 여러 개)
                bboxes = passage.bbox_list if passage.bbox_list else [passage.bbox]
                for bbox in bboxes:
                    # 반투명 배경
                    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
                    overlay_draw = ImageDraw.Draw(overlay)
                    overlay_draw.rectangle(
                        [bbox.x1, bbox.y1, bbox.x2, bbox.y2],
                        fill=(255, 165, 0, 50)  # 주황색 반투명
                    )
                    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
                    draw = ImageDraw.Draw(img)

                    # 테두리 (점선 효과)
                    for offset in range(2):
                        draw.rectangle(
                            [bbox.x1 - offset, bbox.y1 - offset, bbox.x2 + offset, bbox.y2 + offset],
                            outline=passage_color
                        )

                # 지문 라벨 (첫 번째 bbox에만)
                first_bbox = bboxes[0]
                label = f"[{passage.item_range}]"
                draw.rectangle(
                    [first_bbox.x1, first_bbox.y1 - 25, first_bbox.x1 + 80, first_bbox.y1],
                    fill=passage_color
                )
                draw.text((first_bbox.x1 + 5, first_bbox.y1 - 22), label, fill="white")

        # 문항 bbox 그리기
        for idx, item in enumerate(items):
            color = item_colors[idx % len(item_colors)]
            bbox = item.bbox

            # 박스 그리기 (두꺼운 선)
            for offset in range(3):
                draw.rectangle(
                    [bbox.x1 - offset, bbox.y1 - offset, bbox.x2 + offset, bbox.y2 + offset],
                    outline=color
                )

            # 문항 번호 라벨
            label = f"#{item.item_number}"
            if item.passage_ref:
                label += "*"  # 지문 참조 표시
            draw.rectangle(
                [bbox.x1, bbox.y1 - 25, bbox.x1 + 60, bbox.y1],
                fill=color
            )
            draw.text((bbox.x1 + 5, bbox.y1 - 22), label, fill="white")

        # 저장
        filename = f"page_{page_number}_segmented.png"
        output_path = output_dir / filename

        img.save(output_path, "PNG")
        return output_path

    def save_all_pages_with_boxes(
        self,
        items: list[ExtractedItem],
        output_dir: Path,
        passages: list[PassageInfo] = None
    ) -> list[Path]:
        """모든 페이지에 bbox를 표시하여 저장

        Args:
            items: 추출된 문항 목록
            output_dir: 출력 디렉토리
            passages: 공유 지문 목록

        Returns:
            저장된 파일 경로 목록
        """
        from collections import defaultdict

        # 페이지별로 문항 그룹화
        page_items = defaultdict(list)
        for item in items:
            page_items[item.page_number].append(item)

        # 페이지별로 지문 그룹화
        page_passages = defaultdict(list)
        if passages:
            for passage in passages:
                page_passages[passage.page_number].append(passage)

        saved_paths = []
        for page_num in sorted(page_items.keys()):
            page_passage_list = page_passages.get(page_num, [])
            path = self.save_page_with_boxes(
                page_num, page_items[page_num], output_dir, page_passage_list
            )
            saved_paths.append(path)
            passage_info = f", {len(page_passage_list)}개 지문" if page_passage_list else ""
            print(f"  저장: {path.name} ({len(page_items[page_num])}개 문항{passage_info})")

        return saved_paths

    def get_text_blocks(self, page_number: int) -> list[dict]:
        """페이지의 텍스트 블록 추출 (참고용)

        Args:
            page_number: 페이지 번호

        Returns:
            텍스트 블록 목록
        """
        page_idx = page_number - 1
        page = self.doc[page_idx]

        zoom = self.dpi / 72.0
        blocks = page.get_text("dict")["blocks"]

        result = []
        for block in blocks:
            if block.get("type") == 0:  # 텍스트 블록
                bbox = block.get("bbox", [0, 0, 0, 0])
                # DPI 스케일 적용
                scaled_bbox = [
                    bbox[0] * zoom,
                    bbox[1] * zoom,
                    bbox[2] * zoom,
                    bbox[3] * zoom
                ]

                text = ""
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text += span.get("text", "")
                    text += "\n"

                result.append({
                    "bbox": scaled_bbox,
                    "text": text.strip()
                })

        return result
