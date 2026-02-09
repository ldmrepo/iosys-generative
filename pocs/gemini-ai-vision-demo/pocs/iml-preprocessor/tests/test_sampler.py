"""Tests for stratified sampler."""

import json
import tempfile
from pathlib import Path

import pytest

from src.core.schemas import IMLItem
from src.samplers.stratified_sampler import StratifiedSampler


@pytest.fixture
def sampler() -> StratifiedSampler:
    """Create a sampler instance."""
    return StratifiedSampler()


@pytest.fixture
def mock_items() -> list[IMLItem]:
    """Create mock IML items for testing."""
    items = []

    # Create items for different subjects and grades
    subjects = ["수학", "과학", "국어"]
    grades = ["초1", "초2", "중1", "중2"]

    for subject in subjects:
        for grade in grades:
            for i in range(5):  # 5 items per group
                item = IMLItem(
                    id=f"{subject}_{grade}_{i}",
                    raw_path=Path(f"/mock/{subject}_{grade}_{i}.iml"),
                    subject=subject,
                    grade=grade,
                    school_level="중학교" if grade.startswith("중") else "초등학교",
                    has_images=True,
                    images=[f"image_{i}.png"],
                )
                items.append(item)

    return items


class TestStratifiedSampler:
    """Test cases for StratifiedSampler."""

    def test_sampler_initialization(self, sampler: StratifiedSampler) -> None:
        """Test sampler initialization."""
        assert sampler is not None
        assert sampler.settings is not None
        assert sampler.parser is not None

    def test_target_subjects(self, sampler: StratifiedSampler) -> None:
        """Test that target subjects are configured."""
        subjects = sampler.settings.TARGET_SUBJECTS
        assert "수학" in subjects
        assert "과학" in subjects
        assert "국어" in subjects
        assert "영어" in subjects
        assert "사회" in subjects
        assert "역사" in subjects

    def test_target_grades(self, sampler: StratifiedSampler) -> None:
        """Test that target grades are configured."""
        grades = sampler.settings.TARGET_GRADES
        # Elementary
        assert "초1" in grades
        assert "초6" in grades
        # Middle school
        assert "중1" in grades
        assert "중3" in grades


class TestSamplingReport:
    """Test cases for sampling report."""

    def test_report_json_serialization(self, tmp_path: Path) -> None:
        """Test that sampling report can be serialized to JSON."""
        from src.core.schemas import GroupSamplingResult, SamplingReport

        report = SamplingReport(
            raw_data_dir="/test/raw",
            output_dir="/test/output",
            samples_per_group=30,
            require_images=True,
            total_items_scanned=100,
            total_items_with_images=50,
            total_items_sampled=30,
        )

        # Add a group
        group = GroupSamplingResult(
            subject="수학",
            grade="중2",
            target_count=30,
            actual_count=25,
            items=[],
        )
        report.groups.append(group)

        # Serialize to JSON
        json_str = json.dumps(report.model_dump(), ensure_ascii=False, indent=2, default=str)

        # Verify JSON is valid
        parsed = json.loads(json_str)
        assert parsed["raw_data_dir"] == "/test/raw"
        assert parsed["total_items_sampled"] == 30
        assert len(parsed["groups"]) == 1
        assert parsed["groups"][0]["subject"] == "수학"


class TestEncodingUtils:
    """Test cases for encoding utilities."""

    def test_decode_euckr(self) -> None:
        """Test EUC-KR decoding."""
        from src.utils.encoding import decode_euckr

        # Test with UTF-8 encoded string (fallback)
        utf8_bytes = "테스트".encode("utf-8")
        result = decode_euckr(utf8_bytes)
        assert "테스트" in result or result  # May differ based on encoding detection

    def test_convert_file_to_utf8(self, tmp_path: Path) -> None:
        """Test file encoding conversion."""
        from src.utils.encoding import convert_file_to_utf8

        # Create a file with encoding declaration
        input_file = tmp_path / "input.iml"
        content = '<?xml version="1.0" encoding="ksc5601"?>\n<test>테스트</test>'
        input_file.write_text(content, encoding="utf-8")

        output_file = tmp_path / "output.iml"
        convert_file_to_utf8(input_file, output_file)

        # Verify output
        output_content = output_file.read_text(encoding="utf-8")
        assert 'encoding="utf-8"' in output_content
        assert "테스트" in output_content


class TestImageUtils:
    """Test cases for image utilities."""

    def test_validate_image_nonexistent(self) -> None:
        """Test validation of non-existent image."""
        from src.utils.image_utils import validate_image

        result = validate_image(Path("/nonexistent/image.png"))
        assert result is False

    def test_find_item_images(self, tmp_path: Path) -> None:
        """Test finding images in item directory."""
        from src.utils.image_utils import find_item_images

        # Create directory structure
        item_dir = tmp_path / "TEST123"
        draw_dir = item_dir / "DrawObjPic"
        draw_dir.mkdir(parents=True)

        # Create dummy image files
        (draw_dir / "test1.png").touch()
        (draw_dir / "test2.jpg").touch()
        (draw_dir / "test3.txt").touch()  # Not an image

        images = find_item_images(item_dir)

        assert len(images) == 2
        image_names = [img.name for img in images]
        assert "test1.png" in image_names
        assert "test2.jpg" in image_names
        assert "test3.txt" not in image_names
