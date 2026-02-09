"""Tests for IML parser."""

import tempfile
from pathlib import Path

import pytest

from src.parsers.iml_parser import IMLParser


SAMPLE_IML_CONTENT = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<문항종류>
<단위문항>
<문항 id="TEST123" iOrder="-1" qt="11 선택형" df="03 중" cls2="02 중학교" cls3="08 2학년" cls4="03 수학" kw="방정식, 일차방정식">
<문제>
<물음>
<단락 justv="0">
<문자열>다음 방정식의 해를 구하시오.</문자열>
</단락>
</물음>
<답항>
<단락 justv="0">
<문자열>x = 1</문자열>
</단락>
</답항>
<답항>
<단락 justv="0">
<문자열>x = 2</문자열>
</단락>
</답항>
<답항>
<단락 justv="0">
<문자열>x = 3</문자열>
</단락>
</답항>
</문제>
<정답>
<단락 justv="0">
<문자열>2</문자열>
</단락>
</정답>
<해설>
<단락 justv="0">
<문자열>방정식을 풀면 x = 2가 됩니다.</문자열>
</단락>
</해설>
</문항>
</단위문항>
</문항종류>
"""


@pytest.fixture
def parser() -> IMLParser:
    """Create a parser instance."""
    return IMLParser()


@pytest.fixture
def sample_iml_file(tmp_path: Path) -> Path:
    """Create a sample IML file."""
    iml_path = tmp_path / "test.iml"
    iml_path.write_text(SAMPLE_IML_CONTENT, encoding="utf-8")
    return iml_path


class TestIMLParser:
    """Test cases for IMLParser."""

    def test_parse_file(self, parser: IMLParser, sample_iml_file: Path) -> None:
        """Test parsing a valid IML file."""
        item = parser.parse_file(sample_iml_file)

        assert item is not None
        assert item.id == "TEST123"
        assert item.subject == "수학"
        assert item.grade == "중2"
        assert item.school_level == "중학교"
        assert item.question_type == "선택형"
        assert item.difficulty == "중"

    def test_parse_stem(self, parser: IMLParser, sample_iml_file: Path) -> None:
        """Test extracting the question stem."""
        item = parser.parse_file(sample_iml_file)

        assert item is not None
        assert "방정식" in item.stem
        assert "해를 구하시오" in item.stem

    def test_parse_choices(self, parser: IMLParser, sample_iml_file: Path) -> None:
        """Test extracting answer choices."""
        item = parser.parse_file(sample_iml_file)

        assert item is not None
        assert len(item.choices) == 3
        assert "x = 1" in item.choices[0]
        assert "x = 2" in item.choices[1]
        assert "x = 3" in item.choices[2]

    def test_parse_answer(self, parser: IMLParser, sample_iml_file: Path) -> None:
        """Test extracting the correct answer."""
        item = parser.parse_file(sample_iml_file)

        assert item is not None
        assert "2" in item.answer

    def test_parse_explanation(self, parser: IMLParser, sample_iml_file: Path) -> None:
        """Test extracting the explanation."""
        item = parser.parse_file(sample_iml_file)

        assert item is not None
        assert "방정식을 풀면" in item.explanation

    def test_parse_keywords(self, parser: IMLParser, sample_iml_file: Path) -> None:
        """Test extracting keywords."""
        item = parser.parse_file(sample_iml_file)

        assert item is not None
        assert "방정식" in item.keywords
        assert "일차방정식" in item.keywords

    def test_parse_nonexistent_file(self, parser: IMLParser, tmp_path: Path) -> None:
        """Test parsing a non-existent file."""
        item = parser.parse_file(tmp_path / "nonexistent.iml")
        assert item is None

    def test_parse_invalid_xml(self, parser: IMLParser, tmp_path: Path) -> None:
        """Test parsing invalid XML."""
        invalid_file = tmp_path / "invalid.iml"
        invalid_file.write_text("This is not XML", encoding="utf-8")

        item = parser.parse_file(invalid_file)
        assert item is None

    def test_extract_code(self, parser: IMLParser) -> None:
        """Test code extraction from classification values."""
        assert parser._extract_code("03 수학") == "03"
        assert parser._extract_code("08 2학년") == "08"
        assert parser._extract_code("") == ""
        assert parser._extract_code("11 선택형") == "11"

    def test_get_grade_name(self, parser: IMLParser) -> None:
        """Test grade name mapping."""
        # Elementary school
        assert parser._get_grade_name("01", "01") == "초1"
        assert parser._get_grade_name("06", "01") == "초6"

        # Middle school
        assert parser._get_grade_name("07", "02") == "중1"
        assert parser._get_grade_name("08", "02") == "중2"
        assert parser._get_grade_name("09", "02") == "중3"

        # Alternative middle school coding
        assert parser._get_grade_name("01", "02") == "중1"
        assert parser._get_grade_name("02", "02") == "중2"


class TestIMLParserWithImages:
    """Test cases for IML parser with image handling."""

    def test_has_images_flag_false(self, parser: IMLParser, sample_iml_file: Path) -> None:
        """Test that has_images is False when no images."""
        item = parser.parse_file(sample_iml_file)

        assert item is not None
        assert item.has_images is False
        assert len(item.images) == 0

    def test_parse_iml_with_image_element(self, parser: IMLParser, tmp_path: Path) -> None:
        """Test parsing IML with 그림 element."""
        iml_content = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<문항종류>
<단위문항>
<문항 id="IMG123" qt="11 선택형" df="03 중" cls2="02 중학교" cls3="08 2학년" cls4="03 수학">
<문제>
<물음>
<단락 justv="0">
<문자열>그림을 보고 답하시오.</문자열>
</단락>
<그림 w="50" h="30" name="test_image">IMG123\\DrawObjPic\\test.png</그림>
</물음>
</문제>
</문항>
</단위문항>
</문항종류>
"""
        iml_file = tmp_path / "image_test.iml"
        iml_file.write_text(iml_content, encoding="utf-8")

        item = parser.parse_file(iml_file)

        assert item is not None
        assert len(item.images) >= 1
        # The image path should be extracted
        assert any("DrawObjPic" in img or "test.png" in img for img in item.images)
