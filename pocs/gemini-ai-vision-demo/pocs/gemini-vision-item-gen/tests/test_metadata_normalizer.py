"""MetadataNormalizer 테스트"""

import pytest
from src.utils.metadata_normalizer import MetadataNormalizer


@pytest.fixture
def normalizer():
    return MetadataNormalizer()


class TestNormalizeSubject:
    """과목 정규화 테스트"""

    def test_normalize_subject_by_code(self, normalizer):
        """코드로 과목 정규화"""
        assert normalizer.normalize_subject("03") == "수학"
        assert normalizer.normalize_subject("01") == "국어"
        assert normalizer.normalize_subject("05") == "과학"

    def test_normalize_subject_by_name(self, normalizer):
        """이름으로 과목 정규화"""
        assert normalizer.normalize_subject("수학") == "수학"
        assert normalizer.normalize_subject("영어") == "영어"

    def test_normalize_subject_by_code_with_name(self, normalizer):
        """코드+이름 형식 정규화"""
        assert normalizer.normalize_subject("03 수학") == "수학"
        assert normalizer.normalize_subject("02 영어") == "영어"

    def test_normalize_subject_empty(self, normalizer):
        """빈 값 기본값 반환"""
        result = normalizer.normalize_subject("")
        assert result == "수학"  # DEFAULT_SUBJECT

    def test_normalize_subject_invalid(self, normalizer):
        """유효하지 않은 값"""
        result = normalizer.normalize_subject("99")
        assert result == "수학"  # 기본값


class TestNormalizeGrade:
    """학년 정규화 테스트"""

    def test_normalize_grade_by_code(self, normalizer):
        """코드로 학년 정규화"""
        assert normalizer.normalize_grade("07") == "중1"
        assert normalizer.normalize_grade("08") == "중2"
        assert normalizer.normalize_grade("01") == "초1"

    def test_normalize_grade_standard_format(self, normalizer):
        """표준 형식 그대로 반환"""
        assert normalizer.normalize_grade("중2") == "중2"
        assert normalizer.normalize_grade("고1") == "고1"
        assert normalizer.normalize_grade("초3") == "초3"

    def test_normalize_grade_empty(self, normalizer):
        """빈 값"""
        assert normalizer.normalize_grade("") == ""


class TestNormalizeDifficulty:
    """난이도 정규화 테스트"""

    def test_normalize_difficulty_by_code(self, normalizer):
        """코드로 난이도 정규화"""
        assert normalizer.normalize_difficulty("01") == "easy"
        assert normalizer.normalize_difficulty("02") == "medium"
        assert normalizer.normalize_difficulty("03") == "hard"

    def test_normalize_difficulty_korean(self, normalizer):
        """한글로 난이도 정규화"""
        assert normalizer.normalize_difficulty("상") == "hard"
        assert normalizer.normalize_difficulty("중") == "medium"
        assert normalizer.normalize_difficulty("하") == "easy"

    def test_normalize_difficulty_english(self, normalizer):
        """영문으로 난이도 정규화"""
        assert normalizer.normalize_difficulty("hard") == "hard"
        assert normalizer.normalize_difficulty("MEDIUM") == "medium"
        assert normalizer.normalize_difficulty("Easy") == "easy"

    def test_normalize_difficulty_empty(self, normalizer):
        """빈 값 기본값"""
        assert normalizer.normalize_difficulty("") == "medium"


class TestNormalizeQuestionType:
    """채점유형 정규화 테스트"""

    def test_normalize_question_type_by_code(self, normalizer):
        """코드로 채점유형 정규화"""
        assert normalizer.normalize_question_type("11") == "선택형"
        assert normalizer.normalize_question_type("31") == "단답형"
        assert normalizer.normalize_question_type("41") == "서술형"

    def test_normalize_question_type_by_name(self, normalizer):
        """이름으로 채점유형"""
        assert normalizer.normalize_question_type("선택형") == "선택형"

    def test_normalize_question_type_empty(self, normalizer):
        """빈 값"""
        assert normalizer.normalize_question_type("") == ""


class TestNormalizeAll:
    """전체 정규화 테스트"""

    def test_normalize_full_metadata(self, normalizer):
        """전체 메타데이터 정규화"""
        metadata = {
            "subject": "03 수학",
            "grade": "08",
            "difficulty": "상",
            "question_type": "11",
        }

        result = normalizer.normalize(metadata)

        assert result["subject"] == "수학"
        assert result["subject_code"] == "03"
        assert result["grade"] == "중2"
        assert result["grade_code"] == "08"
        assert result["difficulty"] == "hard"
        assert result["question_type"] == "선택형"
        assert result["school_level"] == "중학교"

    def test_normalize_empty_metadata(self, normalizer):
        """빈 메타데이터"""
        result = normalizer.normalize({})

        assert result["subject"] == "수학"  # 기본값
        assert result["difficulty"] == "medium"  # 기본값

    def test_normalize_none_metadata(self, normalizer):
        """None 메타데이터"""
        result = normalizer.normalize(None)

        assert result["subject"] == "수학"


class TestValidation:
    """유효성 검증 테스트"""

    def test_validate_subject_valid(self, normalizer):
        """유효한 과목"""
        assert normalizer.validate_subject("03")
        assert normalizer.validate_subject("수학")
        assert normalizer.validate_subject("03 수학")

    def test_validate_subject_invalid(self, normalizer):
        """유효하지 않은 과목"""
        assert not normalizer.validate_subject("")
        assert not normalizer.validate_subject("99")
        assert not normalizer.validate_subject("물리")  # 목록에 없음

    def test_validate_grade_valid(self, normalizer):
        """유효한 학년"""
        assert normalizer.validate_grade("08")
        assert normalizer.validate_grade("중2")
        assert normalizer.validate_grade("")  # 빈 값 허용

    def test_validate_difficulty_valid(self, normalizer):
        """유효한 난이도"""
        assert normalizer.validate_difficulty("hard")
        assert normalizer.validate_difficulty("상")
        assert normalizer.validate_difficulty("02")
