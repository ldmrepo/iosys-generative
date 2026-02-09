"""품질 검사기 테스트"""

import pytest
from src.core.schemas import (
    ItemType,
    DifficultyLevel,
    Choice,
    ItemQuestion,
    EvidencePack,
    ValidationStatus,
    FailureCode,
)
from src.validators.quality_checker import QualityChecker


@pytest.fixture
def quality_checker():
    return QualityChecker()


@pytest.fixture
def valid_item():
    """유효한 문항"""
    return ItemQuestion(
        item_id="TEST-001",
        item_type=ItemType.GRAPH,
        difficulty=DifficultyLevel.MEDIUM,
        stem="위 그래프에서 가장 높은 값을 가진 월은 언제인가?",
        choices=[
            Choice(label="A", text="1월"),
            Choice(label="B", text="2월"),
            Choice(label="C", text="3월"),
            Choice(label="D", text="4월"),
        ],
        correct_answer="C",
        explanation="그래프를 보면 3월의 막대가 가장 높으므로 정답은 C입니다.",
        evidence=EvidencePack(
            extracted_facts=["3월 값: 85", "1월 값: 45"],
            analysis_summary="막대 그래프 분석"
        ),
        source_image="/path/to/image.png"
    )


@pytest.fixture
def invalid_item_short_stem():
    """짧은 질문"""
    return ItemQuestion(
        item_id="TEST-002",
        item_type=ItemType.GRAPH,
        stem="질문?",
        choices=[
            Choice(label="A", text="1"),
            Choice(label="B", text="2"),
            Choice(label="C", text="3"),
            Choice(label="D", text="4"),
        ],
        correct_answer="A",
        explanation="해설",
        source_image="/path/to/image.png"
    )


@pytest.fixture
def invalid_item_few_choices():
    """선지 부족"""
    return ItemQuestion(
        item_id="TEST-003",
        item_type=ItemType.GRAPH,
        stem="위 그래프에서 가장 높은 값은?",
        choices=[
            Choice(label="A", text="10"),
            Choice(label="B", text="20"),
        ],
        correct_answer="A",
        explanation="해설입니다.",
        source_image="/path/to/image.png"
    )


@pytest.fixture
def invalid_item_wrong_answer():
    """잘못된 정답"""
    return ItemQuestion(
        item_id="TEST-004",
        item_type=ItemType.GRAPH,
        stem="위 그래프에서 가장 높은 값은?",
        choices=[
            Choice(label="A", text="10"),
            Choice(label="B", text="20"),
            Choice(label="C", text="30"),
            Choice(label="D", text="40"),
        ],
        correct_answer="E",  # 존재하지 않는 선지
        explanation="해설입니다.",
        source_image="/path/to/image.png"
    )


@pytest.fixture
def invalid_item_duplicate_choices():
    """중복 선지"""
    return ItemQuestion(
        item_id="TEST-005",
        item_type=ItemType.GRAPH,
        stem="위 그래프에서 가장 높은 값은?",
        choices=[
            Choice(label="A", text="10개"),
            Choice(label="B", text="20개"),
            Choice(label="C", text="10개"),  # A와 중복
            Choice(label="D", text="40개"),
        ],
        correct_answer="B",
        explanation="해설입니다.",
        source_image="/path/to/image.png"
    )


def test_valid_item_passes(quality_checker, valid_item):
    """유효한 문항은 통과"""
    report = quality_checker.check(valid_item)
    assert report.status == ValidationStatus.PASS
    assert len(report.failure_codes) == 0


def test_short_stem_fails(quality_checker, invalid_item_short_stem):
    """짧은 질문은 실패"""
    report = quality_checker.check(invalid_item_short_stem)
    assert report.status == ValidationStatus.FAIL
    assert FailureCode.INVALID_FORMAT in report.failure_codes


def test_few_choices_fails(quality_checker, invalid_item_few_choices):
    """선지 부족은 실패"""
    report = quality_checker.check(invalid_item_few_choices)
    assert report.status == ValidationStatus.FAIL
    assert FailureCode.INVALID_FORMAT in report.failure_codes


def test_wrong_answer_fails(quality_checker, invalid_item_wrong_answer):
    """잘못된 정답은 실패"""
    report = quality_checker.check(invalid_item_wrong_answer)
    assert report.status == ValidationStatus.FAIL
    assert FailureCode.INVALID_FORMAT in report.failure_codes


def test_duplicate_choices_fails(quality_checker, invalid_item_duplicate_choices):
    """중복 선지는 실패"""
    report = quality_checker.check(invalid_item_duplicate_choices)
    assert report.status == ValidationStatus.FAIL
    assert FailureCode.OPTION_OVERLAP in report.failure_codes


def test_batch_check(quality_checker, valid_item, invalid_item_short_stem):
    """일괄 검사"""
    items = [valid_item, invalid_item_short_stem]
    reports = quality_checker.check_batch(items)

    assert len(reports) == 2
    assert reports[0].status == ValidationStatus.PASS
    assert reports[1].status == ValidationStatus.FAIL
