"""문항 품질 검사 모듈 (규칙 기반)"""

from ..core.schemas import (
    ItemQuestion,
    ValidationReport,
    ValidationStatus,
    FailureCode,
)


class QualityChecker:
    """규칙 기반 문항 품질 검사기"""

    def __init__(self):
        self.min_stem_length = 10
        self.min_choice_count = 4
        self.max_choice_count = 5
        self.min_choice_length = 1
        self.min_explanation_length = 20

    def check(self, item: ItemQuestion) -> ValidationReport:
        """
        규칙 기반 품질 검사

        Args:
            item: 검사할 문항

        Returns:
            ValidationReport
        """
        failure_codes: list[FailureCode] = []
        details: list[str] = []
        recommendations: list[str] = []

        # 1. 질문 길이 검사
        if len(item.stem.strip()) < self.min_stem_length:
            failure_codes.append(FailureCode.INVALID_FORMAT)
            details.append(f"질문이 너무 짧습니다. (최소 {self.min_stem_length}자)")
            recommendations.append("더 명확하고 상세한 질문을 작성하세요.")

        # 2. 선지 개수 검사
        choice_count = len(item.choices)
        if choice_count < self.min_choice_count:
            failure_codes.append(FailureCode.INVALID_FORMAT)
            details.append(f"선지가 부족합니다. ({choice_count}개, 최소 {self.min_choice_count}개)")
            recommendations.append("선지를 추가하세요.")
        elif choice_count > self.max_choice_count:
            details.append(f"선지가 많습니다. ({choice_count}개)")
            recommendations.append("선지 수를 줄이는 것을 고려하세요.")

        # 3. 선지 내용 검사
        for choice in item.choices:
            if len(choice.text.strip()) < self.min_choice_length:
                failure_codes.append(FailureCode.INVALID_FORMAT)
                details.append(f"선지 {choice.label}가 비어있거나 너무 짧습니다.")
                recommendations.append(f"선지 {choice.label}의 내용을 보완하세요.")

        # 4. 정답 유효성 검사
        valid_labels = [c.label for c in item.choices]
        if item.correct_answer not in valid_labels:
            failure_codes.append(FailureCode.INVALID_FORMAT)
            details.append(f"정답 '{item.correct_answer}'이 유효한 선지가 아닙니다.")
            recommendations.append(f"정답을 {valid_labels} 중 하나로 설정하세요.")

        # 5. 해설 길이 검사
        if len(item.explanation.strip()) < self.min_explanation_length:
            details.append(f"해설이 짧습니다. (최소 {self.min_explanation_length}자 권장)")
            recommendations.append("해설을 더 상세하게 작성하세요.")

        # 6. 선지 중복 검사
        choice_texts = [c.text.strip().lower() for c in item.choices]
        if len(choice_texts) != len(set(choice_texts)):
            failure_codes.append(FailureCode.OPTION_OVERLAP)
            details.append("중복되는 선지가 있습니다.")
            recommendations.append("선지 내용을 서로 다르게 수정하세요.")

        # 7. 시각 근거 검사
        if not item.evidence.extracted_facts and not item.evidence.analysis_summary:
            details.append("시각 근거 정보가 부족합니다.")
            recommendations.append("이미지 분석 결과를 다시 확인하세요.")

        # 상태 결정
        if failure_codes:
            status = ValidationStatus.FAIL
        elif details:
            status = ValidationStatus.REVIEW
        else:
            status = ValidationStatus.PASS

        return ValidationReport(
            item_id=item.item_id,
            status=status,
            failure_codes=list(set(failure_codes)),  # 중복 제거
            details=details,
            recommendations=recommendations
        )

    def check_batch(self, items: list[ItemQuestion]) -> list[ValidationReport]:
        """여러 문항 일괄 검사"""
        return [self.check(item) for item in items]
