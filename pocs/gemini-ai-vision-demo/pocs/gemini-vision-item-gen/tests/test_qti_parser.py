"""QTIParser 테스트"""

import pytest
import tempfile
from pathlib import Path

from src.parsers.qti_parser import QTIParser
from src.core.schemas import QTIItem, Choice


@pytest.fixture
def parser():
    return QTIParser()


@pytest.fixture
def sample_iml_content():
    """샘플 IML XML 내용"""
    return '''<?xml version="1.0" encoding="utf-8"?>
<문항종류>
    <단위문항>
        <문항 id="TEST001" qt="11" cls2="02" cls3="08" cls4="03" df="02"
              kw="방정식,대수">
            <문제>
                <물음>
                    <단락 justh="0" justv="0" tidt="0" bidt="0">
                        <문자열>다음 방정식의 해를 구하시오: x + 5 = 10</문자열>
                    </단락>
                </물음>
                <답항>
                    <단락 justh="0" justv="0" tidt="0" bidt="0">
                        <문자열>x = 3</문자열>
                    </단락>
                </답항>
                <답항>
                    <단락 justh="0" justv="0" tidt="0" bidt="0">
                        <문자열>x = 5</문자열>
                    </단락>
                </답항>
                <답항>
                    <단락 justh="0" justv="0" tidt="0" bidt="0">
                        <문자열>x = 7</문자열>
                    </단락>
                </답항>
                <답항>
                    <단락 justh="0" justv="0" tidt="0" bidt="0">
                        <문자열>x = 10</문자열>
                    </단락>
                </답항>
            </문제>
            <정답>
                <단락 justh="0" justv="0" tidt="0" bidt="0">
                    <문자열>②</문자열>
                </단락>
            </정답>
            <해설>
                <단락 justh="0" justv="0" tidt="0" bidt="0">
                    <문자열>x + 5 = 10에서 양변에서 5를 빼면 x = 5입니다.</문자열>
                </단락>
            </해설>
        </문항>
    </단위문항>
</문항종류>'''


@pytest.fixture
def sample_iml_file(sample_iml_content):
    """샘플 IML 파일 생성"""
    fd, temp_path = tempfile.mkstemp(suffix=".iml")
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(sample_iml_content)
        yield Path(temp_path)
    finally:
        import os
        os.close(fd)
        Path(temp_path).unlink(missing_ok=True)


class TestParseFile:
    """파일 파싱 테스트"""

    def test_parse_valid_file(self, parser, sample_iml_file):
        """유효한 IML 파일 파싱"""
        result = parser.parse(sample_iml_file)

        assert result is not None
        assert isinstance(result, QTIItem)
        assert result.item_id == "TEST001"

    def test_parse_nonexistent_file(self, parser):
        """존재하지 않는 파일"""
        result = parser.parse(Path("/nonexistent/file.iml"))
        assert result is None


class TestParseString:
    """문자열 파싱 테스트"""

    def test_parse_string(self, parser, sample_iml_content):
        """XML 문자열 파싱"""
        result = parser.parse_string(sample_iml_content)

        assert result is not None
        assert result.item_id == "TEST001"

    def test_parse_invalid_xml(self, parser):
        """잘못된 XML"""
        result = parser.parse_string("<invalid>xml")
        assert result is None


class TestExtractContent:
    """내용 추출 테스트"""

    def test_extract_stem(self, parser, sample_iml_content):
        """문제 본문 추출"""
        result = parser.parse_string(sample_iml_content)

        assert "방정식" in result.stem
        assert "x + 5 = 10" in result.stem

    def test_extract_choices(self, parser, sample_iml_content):
        """선지 추출"""
        result = parser.parse_string(sample_iml_content)

        assert len(result.choices) == 4
        assert isinstance(result.choices[0], Choice)
        assert "x = 3" in result.choices[0].text

    def test_extract_answer(self, parser, sample_iml_content):
        """정답 추출"""
        result = parser.parse_string(sample_iml_content)

        assert "②" in result.correct_answer

    def test_extract_explanation(self, parser, sample_iml_content):
        """해설 추출"""
        result = parser.parse_string(sample_iml_content)

        assert "x = 5" in result.explanation


class TestExtractMetadata:
    """메타데이터 추출 테스트"""

    def test_extract_subject(self, parser, sample_iml_content):
        """과목 추출"""
        result = parser.parse_string(sample_iml_content)

        assert result.subject_code == "03"
        assert result.subject == "수학"

    def test_extract_grade(self, parser, sample_iml_content):
        """학년 추출"""
        result = parser.parse_string(sample_iml_content)

        assert result.grade_code == "08"
        assert result.grade == "중2"

    def test_extract_question_type(self, parser, sample_iml_content):
        """채점유형 추출"""
        result = parser.parse_string(sample_iml_content)

        assert result.question_type_code == "11"
        assert result.question_type == "선택형"

    def test_extract_difficulty(self, parser, sample_iml_content):
        """난이도 추출"""
        result = parser.parse_string(sample_iml_content)

        assert result.difficulty_code == "02"
        assert result.difficulty == "medium"

    def test_extract_keywords(self, parser, sample_iml_content):
        """키워드 추출"""
        result = parser.parse_string(sample_iml_content)

        assert "방정식" in result.keywords
        assert "대수" in result.keywords


class TestValidateSchema:
    """스키마 검증 테스트"""

    def test_validate_valid_xml(self, parser, sample_iml_content):
        """유효한 XML 검증"""
        is_valid, errors = parser.validate_schema(sample_iml_content)

        assert is_valid
        assert len(errors) == 0

    def test_validate_invalid_xml(self, parser):
        """잘못된 XML 검증"""
        is_valid, errors = parser.validate_schema("<invalid>")

        assert not is_valid
        assert len(errors) > 0

    def test_validate_missing_id(self, parser):
        """ID 없는 문항"""
        xml = '''<?xml version="1.0" encoding="utf-8"?>
        <문항종류>
            <단위문항>
                <문항 qt="11">
                    <문제><물음><단락><문자열>테스트</문자열></단락></물음></문제>
                </문항>
            </단위문항>
        </문항종류>'''

        is_valid, errors = parser.validate_schema(xml)

        assert not is_valid
        assert any("ID" in e for e in errors)


class TestEncodingHandling:
    """인코딩 처리 테스트"""

    def test_utf8_encoding(self, parser):
        """UTF-8 인코딩"""
        xml = '''<?xml version="1.0" encoding="utf-8"?>
        <문항종류>
            <단위문항>
                <문항 id="ENC001" qt="11">
                    <문제><물음><단락><문자열>한글 테스트 문항</문자열></단락></물음></문제>
                </문항>
            </단위문항>
        </문항종류>'''

        result = parser.parse_string(xml)

        assert result is not None
        assert "한글" in result.stem

    def test_fix_encoding_declaration(self, parser):
        """인코딩 선언 수정"""
        # ksc5601 인코딩 선언이 있는 경우 (실제로는 UTF-8로 전달됨)
        xml = '''<?xml version="1.0" encoding="ksc5601"?>
        <문항종류>
            <단위문항>
                <문항 id="ENC002" qt="11">
                    <문제><물음><단락><문자열>테스트</문자열></단락></물음></문제>
                </문항>
            </단위문항>
        </문항종류>'''

        result = parser.parse_string(xml)

        assert result is not None
        assert result.item_id == "ENC002"
