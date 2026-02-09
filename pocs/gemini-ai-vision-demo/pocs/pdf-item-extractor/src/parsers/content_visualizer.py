"""콘텐츠 블록 시각화

크롭된 문항 이미지에 콘텐츠 블록 bbox를 표시합니다.
"""

import io
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from ..core.schemas import ParsedItem, ContentType


class ContentVisualizer:
    """콘텐츠 블록 시각화"""

    # 콘텐츠 타입별 색상
    COLORS = {
        ContentType.TEXT: "#4CAF50",    # 녹색
        ContentType.MATH: "#2196F3",    # 파란색
        ContentType.IMAGE: "#FF9800",   # 주황색
        ContentType.TABLE: "#9C27B0",   # 보라색
        ContentType.CODE: "#607D8B",    # 회색
    }

    # 선택지 색상
    CHOICE_COLOR = "#E91E63"  # 분홍색
    # 보기 박스 색상
    BOXED_COLOR = "#FF5722"   # 진한 주황색

    def visualize_item(
        self,
        parsed_item: ParsedItem,
        output_path: Optional[Path] = None
    ) -> Path:
        """문항 콘텐츠 블록 시각화

        Args:
            parsed_item: 파싱된 문항
            output_path: 출력 경로 (None이면 자동 생성)

        Returns:
            저장된 이미지 경로
        """
        if not parsed_item.source_image:
            raise ValueError("source_image가 없습니다")

        source_path = Path(parsed_item.source_image)
        if not source_path.exists():
            raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {source_path}")

        # 이미지 로드
        img = Image.open(source_path).convert("RGB")
        width, height = img.size
        draw = ImageDraw.Draw(img)

        # 질문 콘텐츠 블록 그리기
        for block in parsed_item.question:
            if block.box_2d:
                self._draw_block(draw, block.box_2d, block.type, width, height)

        # 보기 박스 영역 그리기
        if parsed_item.has_boxed_text and parsed_item.boxed_area:
            self._draw_boxed_area(draw, parsed_item.boxed_area, width, height)

        # 보기 박스 내 콘텐츠 블록 그리기
        for block in parsed_item.boxed_content:
            if block.box_2d:
                self._draw_block(draw, block.box_2d, block.type, width, height)

        # 선택지 그리기
        for choice in parsed_item.choices:
            if choice.box_2d:
                self._draw_choice(draw, choice.box_2d, choice.label, width, height)
            for block in choice.content:
                if block.box_2d:
                    self._draw_block(draw, block.box_2d, block.type, width, height, alpha=0.3)

        # 범례 추가
        self._draw_legend(draw, width, height)

        # 저장
        if output_path is None:
            output_path = source_path.parent / f"{source_path.stem}_visualized.png"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, "PNG")

        return output_path

    def visualize_items(
        self,
        parsed_items: list[ParsedItem],
        output_dir: Path
    ) -> list[Path]:
        """여러 문항 시각화

        Args:
            parsed_items: 파싱된 문항 목록
            output_dir: 출력 디렉토리

        Returns:
            저장된 이미지 경로 목록
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = []
        for item in parsed_items:
            if not item.source_image:
                continue

            try:
                source_name = Path(item.source_image).stem
                output_path = output_dir / f"{source_name}_visualized.png"
                path = self.visualize_item(item, output_path)
                saved_paths.append(path)
                print(f"  문항 {item.item_number}: {path.name}")
            except Exception as e:
                print(f"  문항 {item.item_number}: 시각화 실패 - {e}")

        return saved_paths

    def _draw_block(
        self,
        draw: ImageDraw.ImageDraw,
        box_2d: list[int],
        content_type: ContentType,
        width: int,
        height: int,
        alpha: float = 0.5
    ):
        """콘텐츠 블록 그리기"""
        # 좌표 변환 (0-1000 -> 픽셀)
        y1 = int(box_2d[0] / 1000 * height)
        x1 = int(box_2d[1] / 1000 * width)
        y2 = int(box_2d[2] / 1000 * height)
        x2 = int(box_2d[3] / 1000 * width)

        color = self.COLORS.get(content_type, "#888888")

        # 테두리 그리기
        for offset in range(2):
            draw.rectangle(
                [x1 - offset, y1 - offset, x2 + offset, y2 + offset],
                outline=color
            )

        # 타입 라벨
        label = content_type.value[:4].upper()
        draw.rectangle([x1, y1 - 18, x1 + 40, y1], fill=color)
        draw.text((x1 + 2, y1 - 16), label, fill="white")

    def _draw_choice(
        self,
        draw: ImageDraw.ImageDraw,
        box_2d: list[int],
        label: str,
        width: int,
        height: int
    ):
        """선택지 영역 그리기"""
        y1 = int(box_2d[0] / 1000 * height)
        x1 = int(box_2d[1] / 1000 * width)
        y2 = int(box_2d[2] / 1000 * height)
        x2 = int(box_2d[3] / 1000 * width)

        # 점선 효과 (실선으로 대체)
        draw.rectangle([x1, y1, x2, y2], outline=self.CHOICE_COLOR)

        # 라벨
        draw.rectangle([x1, y1 - 18, x1 + 25, y1], fill=self.CHOICE_COLOR)
        draw.text((x1 + 2, y1 - 16), label, fill="white")

    def _draw_boxed_area(
        self,
        draw: ImageDraw.ImageDraw,
        box_2d: list[int],
        width: int,
        height: int
    ):
        """보기 박스 영역 그리기"""
        y1 = int(box_2d[0] / 1000 * height)
        x1 = int(box_2d[1] / 1000 * width)
        y2 = int(box_2d[2] / 1000 * height)
        x2 = int(box_2d[3] / 1000 * width)

        # 두꺼운 테두리
        for offset in range(3):
            draw.rectangle(
                [x1 - offset, y1 - offset, x2 + offset, y2 + offset],
                outline=self.BOXED_COLOR
            )

        # 라벨
        draw.rectangle([x1, y1 - 20, x1 + 50, y1], fill=self.BOXED_COLOR)
        draw.text((x1 + 2, y1 - 18), "BOXED", fill="white")

    def _draw_legend(
        self,
        draw: ImageDraw.ImageDraw,
        width: int,
        height: int
    ):
        """범례 그리기"""
        legend_items = [
            (ContentType.TEXT, "TEXT"),
            (ContentType.MATH, "MATH"),
            (ContentType.IMAGE, "IMAGE"),
        ]

        x_start = 10
        y_start = height - 25

        for i, (ctype, label) in enumerate(legend_items):
            x = x_start + i * 70
            color = self.COLORS[ctype]
            draw.rectangle([x, y_start, x + 15, y_start + 15], fill=color)
            draw.text((x + 20, y_start), label, fill="#333333")
