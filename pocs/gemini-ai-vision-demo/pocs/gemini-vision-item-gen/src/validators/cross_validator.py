"""교차 검증 모듈 (Cross-Validation)

다중 AI 모델을 활용한 문항 검증.
Level 1: Gemini Flash (기본)
Level 2: + GPT-4o (높은 신뢰)
Level 3: + Gemini Pro (민감 주제)
"""

import json
import os
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod

from ..core.config import settings
from ..core.schemas import (
    ItemQuestion,
    ValidationReport,
    ValidationStatus,
    FailureCode,
)
from ..utils.json_utils import extract_json_from_text


class BaseModelValidator(ABC):
    """모델 검증기 기본 클래스"""

    @abstractmethod
    def validate_item(self, item: ItemQuestion, image_path: Optional[str] = None) -> dict:
        """문항 검증"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """모델 이름"""
        pass


class GeminiFlashValidator(BaseModelValidator):
    """Gemini Flash 검증기 (Level 1)"""

    VALIDATION_PROMPT = """당신은 교육 문항 품질 검수 전문가입니다.

아래 문항의 품질을 검증하고 결과를 JSON으로 반환하세요.

**문항 정보:**
- 질문: {stem}
- 선지:
{choices}
- 정답: {correct_answer}
- 해설: {explanation}

**검증 기준:**
1. 질문이 명확하고 이해하기 쉬운가?
2. 선지가 상호 배타적인가?
3. 정답이 명확하게 하나인가?
4. 해설이 정답 도출 과정을 잘 설명하는가?
5. 문법/맞춤법 오류는 없는가?

반드시 다음 JSON 형식으로 응답하세요:
```json
{{
    "is_valid": true/false,
    "quality_score": 0-100,
    "issues": ["이슈1", "이슈2"],
    "suggestions": ["개선사항1", "개선사항2"]
}}
```"""

    def __init__(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)
            self.available = True
        except Exception:
            self.available = False
            self.model = None

    @property
    def model_name(self) -> str:
        return settings.gemini_model

    def validate_item(self, item: ItemQuestion, image_path: Optional[str] = None) -> dict:
        if not self.available:
            return {"error": "Gemini Flash not available", "is_valid": None}

        choices_text = "\n".join([f"  {c.label}. {c.text}" for c in item.choices])
        prompt = self.VALIDATION_PROMPT.format(
            stem=item.stem,
            choices=choices_text,
            correct_answer=item.correct_answer,
            explanation=item.explanation
        )

        try:
            if image_path and Path(image_path).exists():
                import PIL.Image
                image = PIL.Image.open(image_path)
                response = self.model.generate_content([prompt, image])
            else:
                response = self.model.generate_content(prompt)

            json_str = extract_json_from_text(response.text)
            if json_str:
                return json.loads(json_str)
            return {"error": "Failed to parse response", "is_valid": None}

        except Exception as e:
            return {"error": str(e), "is_valid": None}


class GPT4oValidator(BaseModelValidator):
    """GPT-4o 검증기 (Level 2)"""

    VALIDATION_PROMPT = """You are an expert educational item quality reviewer.

Validate the following item and return results in JSON.

**Item Information:**
- Question: {stem}
- Choices:
{choices}
- Correct Answer: {correct_answer}
- Explanation: {explanation}

**Validation Criteria:**
1. Is the question clear and understandable?
2. Are the choices mutually exclusive?
3. Is there exactly one correct answer?
4. Does the explanation properly explain the answer?
5. Are there any grammar or spelling errors?

Respond in this exact JSON format:
```json
{{
    "is_valid": true/false,
    "quality_score": 0-100,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"]
}}
```"""

    def __init__(self):
        self.api_key = settings.openai_api_key
        self.available = bool(self.api_key)

    @property
    def model_name(self) -> str:
        return settings.openai_model

    def validate_item(self, item: ItemQuestion, image_path: Optional[str] = None) -> dict:
        if not self.available:
            return {"error": "OpenAI API key not configured", "is_valid": None}

        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            choices_text = "\n".join([f"  {c.label}. {c.text}" for c in item.choices])
            prompt = self.VALIDATION_PROMPT.format(
                stem=item.stem,
                choices=choices_text,
                correct_answer=item.correct_answer,
                explanation=item.explanation
            )

            messages = [{"role": "user", "content": prompt}]

            # 이미지가 있고 Vision 모델인 경우
            if image_path and Path(image_path).exists():
                import base64
                with open(image_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode("utf-8")

                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ]
                }]

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=1000
            )

            json_str = extract_json_from_text(response.choices[0].message.content)
            if json_str:
                return json.loads(json_str)
            return {"error": "Failed to parse response", "is_valid": None}

        except ImportError:
            return {"error": "openai package not installed", "is_valid": None}
        except Exception as e:
            return {"error": str(e), "is_valid": None}


class GeminiProValidator(BaseModelValidator):
    """Gemini Pro 검증기 (Level 3 - 민감 주제)"""

    VALIDATION_PROMPT = """당신은 교육 문항의 민감성 및 윤리성을 검토하는 전문가입니다.

아래 문항이 교육적으로 적절한지 검토하세요.

**문항 정보:**
- 질문: {stem}
- 선지:
{choices}
- 정답: {correct_answer}
- 해설: {explanation}

**검토 기준:**
1. 성별, 인종, 종교, 지역에 대한 편향은 없는가?
2. 폭력적이거나 선정적인 내용은 없는가?
3. 정치적으로 편향된 내용은 없는가?
4. 특정 집단을 비하하거나 차별하는 내용은 없는가?
5. 학생들에게 부정적 영향을 줄 수 있는 내용은 없는가?

반드시 다음 JSON 형식으로 응답하세요:
```json
{{
    "is_appropriate": true/false,
    "sensitivity_score": 0-100,
    "concerns": ["우려사항1", "우려사항2"],
    "recommendations": ["권고사항1", "권고사항2"]
}}
```"""

    def __init__(self):
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_pro_model)
            self.available = True
        except Exception:
            self.available = False
            self.model = None

    @property
    def model_name(self) -> str:
        return settings.gemini_pro_model

    def validate_item(self, item: ItemQuestion, image_path: Optional[str] = None) -> dict:
        if not self.available:
            return {"error": "Gemini Pro not available", "is_valid": None}

        choices_text = "\n".join([f"  {c.label}. {c.text}" for c in item.choices])
        prompt = self.VALIDATION_PROMPT.format(
            stem=item.stem,
            choices=choices_text,
            correct_answer=item.correct_answer,
            explanation=item.explanation
        )

        try:
            response = self.model.generate_content(prompt)
            json_str = extract_json_from_text(response.text)
            if json_str:
                result = json.loads(json_str)
                # is_appropriate를 is_valid로 매핑
                result["is_valid"] = result.get("is_appropriate", True)
                return result
            return {"error": "Failed to parse response", "is_valid": None}

        except Exception as e:
            return {"error": str(e), "is_valid": None}


class CrossValidator:
    """교차 검증 통합 클래스

    다중 AI 모델을 활용하여 문항 품질을 검증합니다.

    Levels:
        1: Gemini Flash만 사용 (기본)
        2: Gemini Flash + GPT-4o (높은 신뢰 필요)
        3: Gemini Flash + GPT-4o + Gemini Pro (민감 주제)
    """

    def __init__(self, level: int = 1):
        """
        Args:
            level: 검증 레벨 (1, 2, 3)
        """
        self.level = min(max(level, 1), 3)  # 1-3 범위로 제한
        self._init_validators()

    def _init_validators(self):
        """레벨에 따른 검증기 초기화"""
        self.validators: list[BaseModelValidator] = []

        # Level 1: Gemini Flash (항상 포함)
        self.validators.append(GeminiFlashValidator())

        # Level 2: + GPT-4o
        if self.level >= 2:
            self.validators.append(GPT4oValidator())

        # Level 3: + Gemini Pro
        if self.level >= 3:
            self.validators.append(GeminiProValidator())

    def validate(
        self,
        item: ItemQuestion,
        image_path: Optional[str] = None,
        require_consensus: bool = True
    ) -> ValidationReport:
        """
        교차 검증 수행

        Args:
            item: 검증할 문항
            image_path: 이미지 경로 (있는 경우)
            require_consensus: True면 모든 모델이 동의해야 PASS

        Returns:
            ValidationReport
        """
        failure_codes: list[FailureCode] = []
        details: list[str] = []
        recommendations: list[str] = []

        results: list[dict] = []
        valid_count = 0
        invalid_count = 0
        total_quality_score = 0
        scored_count = 0

        # 각 모델로 검증
        for validator in self.validators:
            result = validator.validate_item(item, image_path)
            result["model"] = validator.model_name
            results.append(result)

            if result.get("error"):
                details.append(f"[{validator.model_name}] 오류: {result['error']}")
                continue

            is_valid = result.get("is_valid")
            if is_valid is True:
                valid_count += 1
            elif is_valid is False:
                invalid_count += 1

            # 품질 점수 집계
            if "quality_score" in result:
                total_quality_score += result["quality_score"]
                scored_count += 1

            # 이슈/우려사항 수집
            for issue in result.get("issues", []) + result.get("concerns", []):
                details.append(f"[{validator.model_name}] {issue}")

            # 개선사항/권고사항 수집
            for suggestion in result.get("suggestions", []) + result.get("recommendations", []):
                recommendations.append(f"[{validator.model_name}] {suggestion}")

        # 합의 기반 상태 결정
        active_validators = len([r for r in results if not r.get("error")])

        if active_validators == 0:
            status = ValidationStatus.REVIEW
            details.append("모든 검증 모델 실패 - 수동 검토 필요")
        elif require_consensus:
            # 모든 활성 모델이 동의해야 PASS
            if invalid_count > 0:
                status = ValidationStatus.FAIL
                failure_codes.append(FailureCode.MULTI_CORRECT)  # 모델 간 불일치
            elif valid_count == active_validators:
                status = ValidationStatus.PASS
            else:
                status = ValidationStatus.REVIEW
        else:
            # 다수결
            if valid_count > invalid_count:
                status = ValidationStatus.PASS
            elif invalid_count > valid_count:
                status = ValidationStatus.FAIL
            else:
                status = ValidationStatus.REVIEW

        # 평균 품질 점수 기록
        avg_quality = total_quality_score / scored_count if scored_count > 0 else 0
        details.insert(0, f"평균 품질 점수: {avg_quality:.1f}/100 (검증 모델 {active_validators}개)")

        return ValidationReport(
            item_id=item.item_id,
            status=status,
            failure_codes=list(set(failure_codes)),
            details=details,
            recommendations=recommendations
        )

    def get_detailed_results(
        self,
        item: ItemQuestion,
        image_path: Optional[str] = None
    ) -> dict:
        """
        상세 검증 결과 반환

        Args:
            item: 검증할 문항
            image_path: 이미지 경로

        Returns:
            각 모델별 상세 결과
        """
        results = {}

        for validator in self.validators:
            result = validator.validate_item(item, image_path)
            results[validator.model_name] = result

        # 요약 정보 추가
        valid_count = sum(1 for r in results.values() if r.get("is_valid") is True)
        total_count = len(results)

        results["_summary"] = {
            "level": self.level,
            "total_validators": total_count,
            "valid_count": valid_count,
            "consensus": valid_count == total_count and total_count > 0
        }

        return results

    def validate_batch(
        self,
        items: list[ItemQuestion],
        require_consensus: bool = True
    ) -> list[ValidationReport]:
        """여러 문항 일괄 검증"""
        return [self.validate(item, require_consensus=require_consensus) for item in items]

    @property
    def available_models(self) -> list[str]:
        """사용 가능한 모델 목록"""
        return [v.model_name for v in self.validators if hasattr(v, "available") and v.available]
