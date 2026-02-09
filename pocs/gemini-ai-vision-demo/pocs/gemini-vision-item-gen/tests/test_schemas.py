"""스키마 테스트"""

import pytest
from src.core.schemas import (
    ItemType,
    DifficultyLevel,
    Choice,
    ItemQuestion,
    EvidencePack,
    ValidationReport,
    ValidationStatus,
    FailureCode,
)


def test_choice_creation():
    """Choice 모델 생성 테스트"""
    choice = Choice(label="A", text="선지 내용")
    assert choice.label == "A"
    assert choice.text == "선지 내용"


def test_evidence_pack_creation():
    """EvidencePack 모델 생성 테스트"""
    evidence = EvidencePack(
        extracted_facts=["사실1", "사실2"],
        analysis_summary="분석 요약"
    )
    assert len(evidence.extracted_facts) == 2
    assert evidence.analysis_summary == "분석 요약"


def test_item_question_creation():
    """ItemQuestion 모델 생성 테스트"""
    item = ItemQuestion(
        item_id="TEST-001",
        item_type=ItemType.GRAPH,
        difficulty=DifficultyLevel.MEDIUM,
        stem="테스트 질문입니다.",
        choices=[
            Choice(label="A", text="선지1"),
            Choice(label="B", text="선지2"),
            Choice(label="C", text="선지3"),
            Choice(label="D", text="선지4"),
        ],
        correct_answer="A",
        explanation="해설입니다.",
        source_image="/path/to/image.png"
    )

    assert item.item_id == "TEST-001"
    assert item.item_type == ItemType.GRAPH
    assert len(item.choices) == 4
    assert item.correct_answer == "A"


def test_validation_report():
    """ValidationReport 모델 테스트"""
    report = ValidationReport(
        item_id="TEST-001",
        status=ValidationStatus.PASS,
        failure_codes=[],
        details=["검수 통과"],
        recommendations=[]
    )

    assert report.status == ValidationStatus.PASS
    assert len(report.failure_codes) == 0


def test_validation_report_with_failures():
    """실패 코드가 있는 ValidationReport 테스트"""
    report = ValidationReport(
        item_id="TEST-002",
        status=ValidationStatus.FAIL,
        failure_codes=[FailureCode.AMBIGUOUS_READ, FailureCode.OPTION_OVERLAP],
        details=["판독 불명확", "선지 중복"],
        recommendations=["재생성 필요"]
    )

    assert report.status == ValidationStatus.FAIL
    assert len(report.failure_codes) == 2
    assert FailureCode.AMBIGUOUS_READ in report.failure_codes
