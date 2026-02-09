"""이미지 처리 유틸리티"""

from pathlib import Path
from typing import Optional, Tuple
from PIL import Image


class ImageProcessor:
    """이미지 전처리 및 검증 유틸리티"""

    # 지원 포맷
    SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}

    # 권장 해상도
    MIN_WIDTH = 200
    MIN_HEIGHT = 200
    MAX_WIDTH = 4096
    MAX_HEIGHT = 4096

    def __init__(self):
        pass

    def validate_image(self, image_path: str | Path) -> Tuple[bool, list[str]]:
        """
        이미지 유효성 검사

        Returns:
            (유효 여부, 경고/오류 메시지 목록)
        """
        path = Path(image_path)
        issues: list[str] = []

        # 파일 존재 확인
        if not path.exists():
            return False, [f"파일이 존재하지 않습니다: {path}"]

        # 확장자 확인
        if path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return False, [f"지원하지 않는 포맷입니다: {path.suffix}"]

        try:
            with Image.open(path) as img:
                width, height = img.size

                # 해상도 검사
                if width < self.MIN_WIDTH or height < self.MIN_HEIGHT:
                    issues.append(
                        f"해상도가 너무 낮습니다: {width}x{height} "
                        f"(최소 {self.MIN_WIDTH}x{self.MIN_HEIGHT})"
                    )

                if width > self.MAX_WIDTH or height > self.MAX_HEIGHT:
                    issues.append(
                        f"해상도가 너무 높습니다: {width}x{height} "
                        f"(최대 {self.MAX_WIDTH}x{self.MAX_HEIGHT})"
                    )

                # 파일 크기 검사 (20MB 제한)
                file_size = path.stat().st_size
                if file_size > 20 * 1024 * 1024:
                    issues.append(f"파일 크기가 너무 큽니다: {file_size / 1024 / 1024:.1f}MB (최대 20MB)")

        except Exception as e:
            return False, [f"이미지를 열 수 없습니다: {str(e)}"]

        return len(issues) == 0, issues

    def get_image_info(self, image_path: str | Path) -> dict:
        """이미지 정보 조회"""
        path = Path(image_path)

        with Image.open(path) as img:
            return {
                "path": str(path),
                "format": img.format,
                "mode": img.mode,
                "width": img.size[0],
                "height": img.size[1],
                "file_size_bytes": path.stat().st_size,
            }

    def resize_if_needed(
        self,
        image_path: str | Path,
        max_dimension: int = 2048,
        output_path: Optional[str | Path] = None
    ) -> Path:
        """
        필요시 이미지 리사이즈

        Args:
            image_path: 원본 이미지 경로
            max_dimension: 최대 크기 (가로/세로)
            output_path: 출력 경로 (없으면 원본 경로에 _resized 추가)

        Returns:
            결과 이미지 경로
        """
        path = Path(image_path)

        with Image.open(path) as img:
            width, height = img.size

            # 리사이즈 필요 여부 확인
            if width <= max_dimension and height <= max_dimension:
                return path

            # 비율 유지하며 리사이즈
            ratio = min(max_dimension / width, max_dimension / height)
            new_size = (int(width * ratio), int(height * ratio))

            resized = img.resize(new_size, Image.Resampling.LANCZOS)

            # 출력 경로 결정
            if output_path:
                out_path = Path(output_path)
            else:
                out_path = path.parent / f"{path.stem}_resized{path.suffix}"

            resized.save(out_path, format=img.format)

            return out_path

    def convert_to_png(self, image_path: str | Path) -> Path:
        """이미지를 PNG로 변환"""
        path = Path(image_path)

        if path.suffix.lower() == ".png":
            return path

        with Image.open(path) as img:
            # RGBA로 변환 (투명도 지원)
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            out_path = path.parent / f"{path.stem}.png"
            img.save(out_path, format="PNG")

            return out_path
