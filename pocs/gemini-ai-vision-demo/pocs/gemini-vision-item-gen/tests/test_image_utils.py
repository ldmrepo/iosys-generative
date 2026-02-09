"""이미지 유틸리티 테스트"""

import pytest
from pathlib import Path
from PIL import Image
import tempfile

from src.utils.image_utils import ImageProcessor


@pytest.fixture
def image_processor():
    return ImageProcessor()


@pytest.fixture
def temp_image():
    """임시 테스트 이미지 생성"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (400, 300), color="white")
        img.save(f.name)
        yield Path(f.name)
    # 테스트 후 정리
    Path(f.name).unlink(missing_ok=True)


@pytest.fixture
def small_image():
    """작은 이미지"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (50, 50), color="white")
        img.save(f.name)
        yield Path(f.name)
    Path(f.name).unlink(missing_ok=True)


def test_validate_valid_image(image_processor, temp_image):
    """유효한 이미지 검증"""
    is_valid, issues = image_processor.validate_image(temp_image)
    assert is_valid
    assert len(issues) == 0


def test_validate_nonexistent_image(image_processor):
    """존재하지 않는 이미지"""
    is_valid, issues = image_processor.validate_image("/nonexistent/image.png")
    assert not is_valid
    assert "존재하지 않습니다" in issues[0]


def test_validate_small_image(image_processor, small_image):
    """작은 이미지 경고"""
    is_valid, issues = image_processor.validate_image(small_image)
    assert not is_valid  # 최소 해상도 미달
    assert any("해상도가 너무 낮습니다" in issue for issue in issues)


def test_get_image_info(image_processor, temp_image):
    """이미지 정보 조회"""
    info = image_processor.get_image_info(temp_image)
    assert info["width"] == 400
    assert info["height"] == 300
    assert info["format"] == "PNG"


def test_resize_not_needed(image_processor, temp_image):
    """리사이즈 불필요"""
    result = image_processor.resize_if_needed(temp_image, max_dimension=1000)
    assert result == temp_image  # 원본 반환


def test_resize_needed(image_processor):
    """리사이즈 필요"""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (3000, 2000), color="white")
        img.save(f.name)
        temp_path = Path(f.name)

    try:
        result = image_processor.resize_if_needed(temp_path, max_dimension=1000)
        assert result != temp_path  # 새 파일 생성

        # 리사이즈된 이미지 확인
        with Image.open(result) as resized:
            assert resized.size[0] <= 1000
            assert resized.size[1] <= 1000
    finally:
        temp_path.unlink(missing_ok=True)
        if result != temp_path:
            result.unlink(missing_ok=True)
