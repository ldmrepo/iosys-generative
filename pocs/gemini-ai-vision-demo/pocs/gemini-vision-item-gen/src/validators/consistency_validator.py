"""문항-이미지 정합성 검증 모듈

v3.0.0: 생성된 이미지 정합성 검증 추가
- ConsistencyValidator: 원본 이미지 ↔ 문항 정합성 검증
- ImageConsistencyValidator: 생성된 이미지 ↔ 문항 정합성 검증
"""

import json
from typing import Optional
from pathlib import Path

from ..core.schemas import (
    ItemQuestion,
    ValidationReport,
    ValidationStatus,
    FailureCode,
)
from ..agents.vision_client import GeminiVisionClient
from ..utils.json_utils import extract_json_from_text


class ConsistencyValidator:
    """문항-이미지 정합성 검증기"""

    VALIDATION_PROMPT = """당신은 교육 문항 검수 전문가입니다.

아래 문항이 이 이미지를 기반으로 올바르게 출제되었는지 검증하세요.

**문항 정보:**
- 질문: {stem}
- 선지:
{choices}
- 정답: {correct_answer}
- 해설: {explanation}

**검증 기준:**
1. 문항의 질문이 이미지에서 확인 가능한 정보를 묻고 있는가?
2. 정답이 이미지에서 검증 가능한가?
3. 오답들이 합리적인 오류인가? (이미지와 완전히 무관하지 않은가?)
4. 해설이 이미지 내용과 일치하는가?
5. 정답이 유일한가? (복수 정답 가능성은 없는가?)

**응답 형식:**
반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "is_valid": true/false,
    "failure_codes": ["AMBIGUOUS_READ", "NO_VISUAL_EVIDENCE", "MULTI_CORRECT", "OPTION_OVERLAP", "OUT_OF_SCOPE"],
    "details": ["상세 설명1", "상세 설명2"],
    "recommendations": ["개선 권고1", "개선 권고2"]
}}
```

failure_codes는 해당하는 것만 포함하세요. 문제가 없으면 빈 배열입니다."""

    def __init__(self, vision_client: Optional[GeminiVisionClient] = None):
        self.vision_client = vision_client or GeminiVisionClient()

    def validate(self, item: ItemQuestion, image_path: Optional[str | Path] = None) -> ValidationReport:
        """
        문항과 이미지 정합성 검증

        Args:
            item: 검증할 문항
            image_path: 이미지 경로 (없으면 item.source_image 사용)

        Returns:
            ValidationReport
        """
        image_path = image_path or item.source_image

        # 선지 포맷팅
        choices_text = "\n".join([f"  {c.label}. {c.text}" for c in item.choices])

        # 검증 프롬프트 생성
        prompt = self.VALIDATION_PROMPT.format(
            stem=item.stem,
            choices=choices_text,
            correct_answer=item.correct_answer,
            explanation=item.explanation
        )

        try:
            # Agentic Vision으로 검증
            result = self.vision_client.analyze_image_with_agentic_vision(
                image_path=image_path,
                prompt=prompt,
                enable_code_execution=True
            )

            # 응답 파싱
            return self._parse_validation_result(item.item_id, result.get("text", ""))

        except Exception as e:
            # 검증 실패 시 기본 리포트
            return ValidationReport(
                item_id=item.item_id,
                status=ValidationStatus.FAIL,
                failure_codes=[FailureCode.INVALID_FORMAT],
                details=[f"검증 중 오류 발생: {str(e)}"],
                recommendations=["문항을 다시 생성하세요."]
            )

    def _parse_validation_result(self, item_id: str, response_text: str) -> ValidationReport:
        """검증 응답 파싱"""
        try:
            # JSON 추출 (공통 유틸리티 사용)
            json_str = extract_json_from_text(response_text)
            if not json_str:
                json_str = "{}"

            data = json.loads(json_str)

            is_valid = data.get("is_valid", False)
            failure_codes_raw = data.get("failure_codes", [])
            details = data.get("details", [])
            recommendations = data.get("recommendations", [])

            # failure_codes 변환
            failure_codes = []
            for code in failure_codes_raw:
                try:
                    failure_codes.append(FailureCode(code))
                except ValueError:
                    pass

            # 상태 결정
            if is_valid:
                status = ValidationStatus.PASS
            elif failure_codes:
                status = ValidationStatus.FAIL
            else:
                status = ValidationStatus.REVIEW

            return ValidationReport(
                item_id=item_id,
                status=status,
                failure_codes=failure_codes,
                details=details,
                recommendations=recommendations
            )

        except (json.JSONDecodeError, AttributeError):
            return ValidationReport(
                item_id=item_id,
                status=ValidationStatus.REVIEW,
                failure_codes=[],
                details=["검증 응답 파싱 실패"],
                recommendations=["수동 검토 필요"]
            )

    def validate_batch(self, items: list[ItemQuestion]) -> list[ValidationReport]:
        """여러 문항 일괄 검증"""
        reports = []
        for item in items:
            report = self.validate(item)
            reports.append(report)
        return reports


class ImageConsistencyValidator:
    """v3.0.0: 생성된 이미지 ↔ 문항 정합성 검증기

    P5-OUTPUT에서 생성된 이미지가 문항 내용과 일치하는지 검증합니다.
    """

    VALIDATION_PROMPT = """당신은 교육 문항 검수 전문가입니다.

생성된 이미지가 아래 문항의 시각 자료 요구사항과 일치하는지 검증하세요.

**문항 정보:**
- 질문: {stem}
- 선지:
{choices}
- 정답: {correct_answer}

**필요한 시각 자료 설명:**
{image_prompt}

**검증 기준:**
1. 생성된 이미지가 문항에서 요구하는 시각 자료와 일치하는가?
2. 이미지에 필요한 정보가 모두 포함되어 있는가?
3. 이미지가 문항을 풀기에 충분한가?
4. 이미지에 문항과 무관한 요소가 포함되어 있지 않은가?
5. 이미지 품질이 교육용으로 적합한가?

**응답 형식:**
반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "is_consistent": true/false,
    "consistency_score": 0.0-1.0,
    "missing_elements": ["누락된 요소1", "누락된 요소2"],
    "extra_elements": ["불필요한 요소1"],
    "quality_issues": ["품질 문제1"],
    "details": ["상세 설명1", "상세 설명2"],
    "recommendations": ["개선 권고1", "개선 권고2"]
}}
```"""

    def __init__(self, vision_client: Optional[GeminiVisionClient] = None):
        self.vision_client = vision_client or GeminiVisionClient()

    def validate(
        self,
        item: ItemQuestion,
        generated_image_path: str | Path
    ) -> ValidationReport:
        """생성된 이미지와 문항 정합성 검증

        Args:
            item: 검증할 문항
            generated_image_path: 생성된 이미지 경로

        Returns:
            ValidationReport
        """
        generated_image_path = Path(generated_image_path)

        if not generated_image_path.exists():
            return ValidationReport(
                item_id=item.item_id,
                status=ValidationStatus.FAIL,
                failure_codes=[FailureCode.INVALID_FORMAT],
                details=["생성된 이미지 파일이 존재하지 않습니다."],
                recommendations=["이미지를 다시 생성하세요."]
            )

        # 선지 포맷팅
        choices_text = "\n".join([f"  {c.label}. {c.text}" for c in item.choices])

        # 필요한 시각 자료 설명 추출
        image_prompt = ""
        if item.visual_spec and item.visual_spec.image_prompt:
            image_prompt = item.visual_spec.image_prompt
        elif item.visual_spec and item.visual_spec.description:
            image_prompt = item.visual_spec.description
        else:
            image_prompt = f"문항 '{item.stem[:100]}'에 대한 시각 자료"

        # 검증 프롬프트 생성
        prompt = self.VALIDATION_PROMPT.format(
            stem=item.stem,
            choices=choices_text,
            correct_answer=item.correct_answer,
            image_prompt=image_prompt,
        )

        try:
            # Vision 모델로 생성된 이미지 분석 및 검증
            result = self.vision_client.analyze_image_with_agentic_vision(
                image_path=generated_image_path,
                prompt=prompt,
                enable_code_execution=False
            )

            # 응답 파싱
            return self._parse_validation_result(item.item_id, result.get("text", ""))

        except Exception as e:
            return ValidationReport(
                item_id=item.item_id,
                status=ValidationStatus.FAIL,
                failure_codes=[FailureCode.INVALID_FORMAT],
                details=[f"이미지 정합성 검증 중 오류 발생: {str(e)}"],
                recommendations=["이미지를 다시 생성하거나 수동 검토하세요."]
            )

    def _parse_validation_result(self, item_id: str, response_text: str) -> ValidationReport:
        """검증 응답 파싱"""
        try:
            json_str = extract_json_from_text(response_text)
            if not json_str:
                json_str = "{}"

            data = json.loads(json_str)

            is_consistent = data.get("is_consistent", False)
            consistency_score = data.get("consistency_score", 0.0)
            missing_elements = data.get("missing_elements", [])
            extra_elements = data.get("extra_elements", [])
            quality_issues = data.get("quality_issues", [])
            details = data.get("details", [])
            recommendations = data.get("recommendations", [])

            # 상세 내용 구성
            all_details = details.copy()
            if missing_elements:
                all_details.append(f"누락된 요소: {', '.join(missing_elements)}")
            if extra_elements:
                all_details.append(f"불필요한 요소: {', '.join(extra_elements)}")
            if quality_issues:
                all_details.append(f"품질 문제: {', '.join(quality_issues)}")
            all_details.append(f"정합성 점수: {consistency_score:.2f}")

            # 실패 코드 결정
            failure_codes = []
            if not is_consistent:
                failure_codes.append(FailureCode.NO_VISUAL_EVIDENCE)
            if missing_elements:
                failure_codes.append(FailureCode.AMBIGUOUS_READ)

            # 상태 결정
            if is_consistent and consistency_score >= 0.7:
                status = ValidationStatus.PASS
            elif consistency_score >= 0.5:
                status = ValidationStatus.REVIEW
            else:
                status = ValidationStatus.FAIL

            return ValidationReport(
                item_id=item_id,
                status=status,
                failure_codes=failure_codes,
                details=all_details,
                recommendations=recommendations
            )

        except (json.JSONDecodeError, AttributeError):
            return ValidationReport(
                item_id=item_id,
                status=ValidationStatus.REVIEW,
                failure_codes=[],
                details=["이미지 정합성 검증 응답 파싱 실패"],
                recommendations=["수동 검토 필요"]
            )
