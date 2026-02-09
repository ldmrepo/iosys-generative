"""문항 생성 에이전트

v3.0.0: 모델 기반 End-to-End 파이프라인
- 하드코딩된 PROMPTS 딕셔너리 대신 동적 프롬프트 생성
- 문항 생성 시 visual_spec.image_prompt도 함께 출력
- 이미지 설명(자연어)을 입력으로 받아 문항 생성
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.config import settings
from ..core.schemas import (
    ItemQuestion,
    ItemType,
    DifficultyLevel,
    Choice,
    EvidencePack,
    GenerationLog,
    VariationType,
    QTIItem,
    VisualSpec,
)
from ..utils.json_utils import extract_json_from_text
from .vision_client import GeminiVisionClient


class ItemGeneratorAgent:
    """이미지 기반 문항 생성 에이전트

    v3.0.0: 동적 프롬프트 생성 + visual_spec.image_prompt 출력
    - 하드코딩된 프롬프트 대신 이미지 설명 기반 동적 프롬프트 생성
    - LLM이 문항 + 시각 자료 설명을 함께 출력
    """

    # v3.0.0: 동적 문항 생성 프롬프트 (이미지 설명 기반)
    GENERATION_PROMPT_TEMPLATE = """당신은 교육 문항 생성 전문가입니다.

[이미지 분석 결과]
{image_description}

[이미지 유형]: {content_type}
[시각 요소]: {visual_elements}

[작업]
위 이미지 분석 결과를 바탕으로 교육용 객관식 문항 1개를 생성하세요.

**문항 생성 규칙:**
1. 이미지에서 직접 확인 가능한 정보만 사용하세요.
2. 추론이 불가능한 정보는 사용하지 마세요.
3. 정답은 반드시 이미지에서 검증 가능해야 합니다.
4. 오답(오답지)은 합리적인 오류여야 합니다.

**시각 자료 생성 지시:**
- 문항에 이미지가 필요한 경우, visual_spec에 이미지 생성을 위한 상세 설명을 작성하세요.
- 원본 이미지를 재현하거나, 문항에 맞게 변형된 새로운 이미지를 설명하세요.
- 교과서/시험지 스타일로 깔끔하게 설명하세요.

{difficulty_instruction}

반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "stem": "문항 질문",
    "choices": [
        {{"label": "A", "text": "선지1"}},
        {{"label": "B", "text": "선지2"}},
        {{"label": "C", "text": "선지3"}},
        {{"label": "D", "text": "선지4"}}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설 (시각 근거 포함)",
    "evidence_facts": ["근거1", "근거2"],
    "visual_spec": {{
        "required": true,
        "image_prompt": "이 문항에 필요한 이미지를 생성하기 위한 상세 설명. 예: '빨간색 원 안에 담배 그림이 있고 대각선 금지 표시가 그려진 금연 표지판. 표지판 아래에 No Smoking 텍스트. 흰색 배경, 교과서 스타일로 깔끔하게.'",
        "subject_context": "과목/맥락 (예: 영어/표지판 읽기, 수학/함수 그래프)",
        "style_guidance": "스타일 가이드 (예: 교과서풍, 사실적, 간결한 다이어그램)"
    }}
}}
```

visual_spec.image_prompt는 이미지 생성 AI에 직접 전달됩니다. 최대한 구체적으로 작성하세요."""

    # 레거시: 하드코딩된 프롬프트 (하위 호환성)
    PROMPTS = {
        ItemType.GRAPH: """이 이미지는 그래프입니다.

**분석 지시:**
1. 그래프의 유형(막대, 선, 원 등)을 파악하세요.
2. 필요하다면 특정 구간을 확대하여 수치를 정확히 확인하세요.
3. 축의 레이블, 범례, 데이터 포인트를 정확히 읽으세요.

**출력 요구사항:**
그래프에서 직접 확인 가능한 정보만을 사용하여 다음 형식으로 객관식 문항 1개를 생성하세요.

반드시 다음 JSON 형식으로만 응답하세요:
```json
{
    "stem": "문항 질문",
    "choices": [
        {"label": "A", "text": "선지1"},
        {"label": "B", "text": "선지2"},
        {"label": "C", "text": "선지3"},
        {"label": "D", "text": "선지4"}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설 (시각 근거 포함)",
    "evidence_facts": ["근거1", "근거2"]
}
```

추론 불가능한 정보는 사용하지 마세요.""",

        ItemType.GEOMETRY: """이 이미지는 도형입니다.

**분석 지시:**
1. 도형의 종류와 특성을 파악하세요.
2. 길이, 각도, 위치 관계를 분석하세요.
3. 필요 시 특정 부분을 확대하여 판단하세요.

**출력 요구사항:**
시각적 근거가 명확한 조건만을 사용하여 다음 형식으로 객관식 문항 1개를 생성하세요.

반드시 다음 JSON 형식으로만 응답하세요:
```json
{
    "stem": "문항 질문",
    "choices": [
        {"label": "A", "text": "선지1"},
        {"label": "B", "text": "선지2"},
        {"label": "C", "text": "선지3"},
        {"label": "D", "text": "선지4"}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설 (시각 근거 포함)",
    "evidence_facts": ["근거1", "근거2"]
}
```

이미지에서 확인할 수 없는 값은 추정하지 마세요.""",

        ItemType.MEASUREMENT: """이 이미지는 측정 기기 또는 측정값이 포함된 이미지입니다.

**분석 지시:**
1. 측정 기기의 종류를 파악하세요.
2. 눈금과 단위를 정확히 확인하세요.
3. 판독이 어려운 경우 해당 영역을 확대하세요.

**출력 요구사항:**
이미지로 검증 가능한 측정값만을 사용하여 다음 형식으로 객관식 문항 1개를 생성하세요.

반드시 다음 JSON 형식으로만 응답하세요:
```json
{
    "stem": "문항 질문",
    "choices": [
        {"label": "A", "text": "선지1"},
        {"label": "B", "text": "선지2"},
        {"label": "C", "text": "선지3"},
        {"label": "D", "text": "선지4"}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설 (시각 근거 포함)",
    "evidence_facts": ["근거1", "근거2"]
}
```

측정값의 정확성이 핵심입니다.""",
    }

    # 변형 유형별 프롬프트 템플릿
    VARIATION_PROMPTS = {
        VariationType.SIMILAR: """원본 문항을 바탕으로 **유사 문항**을 생성하세요.

**원본 문항:**
- 질문: {stem}
- 선지: {choices}
- 정답: {correct_answer}
- 해설: {explanation}

**변형 규칙:**
1. 문항 구조와 난이도는 동일하게 유지
2. 수치, 데이터 값만 변경 (예: 15% → 23%, 2020년 → 2021년)
3. 정답의 위치(레이블)는 변경 가능
4. 동일한 개념/스킬을 평가해야 함

반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "stem": "변형된 질문",
    "choices": [
        {{"label": "A", "text": "선지1"}},
        {{"label": "B", "text": "선지2"}},
        {{"label": "C", "text": "선지3"}},
        {{"label": "D", "text": "선지4"}}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설",
    "evidence_facts": ["근거1", "근거2"],
    "variation_notes": "변형 내용 요약"
}}
```""",

        VariationType.DIFFICULTY_UP: """원본 문항을 바탕으로 **난이도 상향** 문항을 생성하세요.

**원본 문항:**
- 질문: {stem}
- 선지: {choices}
- 정답: {correct_answer}
- 해설: {explanation}

**난이도 상향 규칙:**
1. 추가 단계의 추론이 필요하도록 변형
2. 복수의 정보 종합이 필요하도록 변형
3. 선지 간 구분이 더 미세하도록 변형
4. 계산이 더 복잡하도록 변형 (수학/과학의 경우)

반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "stem": "난이도 상향된 질문",
    "choices": [
        {{"label": "A", "text": "선지1"}},
        {{"label": "B", "text": "선지2"}},
        {{"label": "C", "text": "선지3"}},
        {{"label": "D", "text": "선지4"}}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설 (난이도 상향 요소 포함)",
    "evidence_facts": ["근거1", "근거2"],
    "variation_notes": "난이도 상향 내용 요약"
}}
```""",

        VariationType.DIFFICULTY_DOWN: """원본 문항을 바탕으로 **난이도 하향** 문항을 생성하세요.

**원본 문항:**
- 질문: {stem}
- 선지: {choices}
- 정답: {correct_answer}
- 해설: {explanation}

**난이도 하향 규칙:**
1. 단순하고 직접적인 질문으로 변형
2. 선지 간 구분을 명확하게 변형
3. 추론 단계를 줄임
4. 직접 읽어서 확인 가능한 정보를 물음

반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "stem": "난이도 하향된 질문",
    "choices": [
        {{"label": "A", "text": "선지1"}},
        {{"label": "B", "text": "선지2"}},
        {{"label": "C", "text": "선지3"}},
        {{"label": "D", "text": "선지4"}}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설",
    "evidence_facts": ["근거1", "근거2"],
    "variation_notes": "난이도 하향 내용 요약"
}}
```""",

        VariationType.CONTEXT_CHANGE: """원본 문항을 바탕으로 **맥락/소재 변경** 문항을 생성하세요.

**원본 문항:**
- 질문: {stem}
- 선지: {choices}
- 정답: {correct_answer}
- 해설: {explanation}

**맥락 변경 규칙:**
1. 동일한 개념/스킬을 평가하되 다른 맥락/소재 사용
2. 예: 인구 그래프 → 매출 그래프, 삼각형 → 사각형
3. 난이도는 동일하게 유지
4. 정답 도출 과정은 유사하게 유지

반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "stem": "맥락 변경된 질문",
    "choices": [
        {{"label": "A", "text": "선지1"}},
        {{"label": "B", "text": "선지2"}},
        {{"label": "C", "text": "선지3"}},
        {{"label": "D", "text": "선지4"}}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설",
    "evidence_facts": ["근거1", "근거2"],
    "variation_notes": "맥락 변경 내용 요약"
}}
```""",

        VariationType.FORMAT_CHANGE: """원본 문항을 바탕으로 **형식 변경** 문항을 생성하세요.

**원본 문항:**
- 질문: {stem}
- 선지: {choices}
- 정답: {correct_answer}
- 해설: {explanation}

**형식 변경 규칙:**
1. 선다형 → 진위형 또는 단답형으로 변경
2. 또는 질문 형식 변경 (빈칸형, 비교형 등)
3. 동일한 개념을 다른 방식으로 평가
4. 난이도는 동일하게 유지

반드시 다음 JSON 형식으로만 응답하세요:
```json
{{
    "stem": "형식 변경된 질문",
    "choices": [
        {{"label": "A", "text": "선지1"}},
        {{"label": "B", "text": "선지2"}},
        {{"label": "C", "text": "선지3"}},
        {{"label": "D", "text": "선지4"}}
    ],
    "correct_answer": "정답 레이블",
    "explanation": "해설",
    "evidence_facts": ["근거1", "근거2"],
    "variation_notes": "형식 변경 내용 요약"
}}
```""",
    }

    def __init__(self, vision_client: Optional[GeminiVisionClient] = None):
        self.vision_client = vision_client or GeminiVisionClient()
        self.generation_logs: list[GenerationLog] = []

    def _build_generation_prompt(
        self,
        image_description: str,
        content_type: str,
        visual_elements: list[str],
        difficulty: DifficultyLevel,
    ) -> str:
        """v3.0.0: 동적 프롬프트 생성

        Args:
            image_description: Vision 모델의 이미지 설명
            content_type: 이미지 유형
            visual_elements: 시각 요소 목록
            difficulty: 난이도

        Returns:
            완성된 프롬프트
        """
        difficulty_instruction = self._get_difficulty_instruction(difficulty)

        return self.GENERATION_PROMPT_TEMPLATE.format(
            image_description=image_description,
            content_type=content_type or "일반 이미지",
            visual_elements=", ".join(visual_elements) if visual_elements else "확인 필요",
            difficulty_instruction=difficulty_instruction,
        )

    def generate_item_with_description(
        self,
        image_path: str | Path,
        image_description: str,
        content_type: str = "",
        visual_elements: list[str] = None,
        item_type: ItemType = ItemType.GRAPH,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
    ) -> tuple[Optional[ItemQuestion], GenerationLog]:
        """v3.0.0: 이미지 설명 기반 문항 생성

        Args:
            image_path: 이미지 경로
            image_description: Vision 모델의 이미지 설명 (P2-ANALYZE 출력)
            content_type: 이미지 유형
            visual_elements: 시각 요소 목록
            item_type: 문항 유형
            difficulty: 난이도

        Returns:
            (생성된 문항, 생성 로그) 튜플
        """
        session_id = str(uuid.uuid4())[:8]
        image_path = Path(image_path)

        gen_log = GenerationLog(
            session_id=session_id,
            source_image=str(image_path),
            item_type=item_type,
        )

        try:
            # 동적 프롬프트 생성
            prompt = self._build_generation_prompt(
                image_description=image_description,
                content_type=content_type,
                visual_elements=visual_elements or [],
                difficulty=difficulty,
            )

            # Agentic Vision으로 문항 생성
            result = self.vision_client.analyze_image_with_agentic_vision(
                image_path=image_path,
                prompt=prompt,
                enable_code_execution=False
            )

            gen_log.phases = self.vision_client.get_phase_logs()
            gen_log.total_duration_ms = result.get("total_duration_ms", 0)

            # EvidencePack 생성 (이미지 설명 포함)
            evidence = EvidencePack(
                image_description=image_description,
                content_type=content_type,
                visual_elements=visual_elements or [],
                analysis_summary=image_description[:500],
            )

            # 응답에서 문항 파싱 (visual_spec 포함)
            item = self._parse_item_from_response(
                response_text=result.get("text", ""),
                item_type=item_type,
                difficulty=difficulty,
                image_path=str(image_path),
                evidence=evidence
            )

            if item:
                gen_log.success = True
                gen_log.final_item_id = item.item_id
            else:
                gen_log.success = False

            self.generation_logs.append(gen_log)
            return item, gen_log

        except Exception as e:
            gen_log.success = False
            phase_logs = self.vision_client.get_phase_logs()
            if phase_logs:
                gen_log.phases = phase_logs
            self.generation_logs.append(gen_log)
            raise RuntimeError(f"문항 생성 실패: {e}") from e

    def generate_item(
        self,
        image_path: str | Path,
        item_type: ItemType,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
        custom_prompt: Optional[str] = None
    ) -> tuple[Optional[ItemQuestion], GenerationLog]:
        """
        이미지에서 문항 생성

        Args:
            image_path: 이미지 경로
            item_type: 문항 유형
            difficulty: 난이도
            custom_prompt: 커스텀 프롬프트 (선택)

        Returns:
            (생성된 문항, 생성 로그) 튜플
        """
        session_id = str(uuid.uuid4())[:8]
        image_path = Path(image_path)

        # 생성 로그 초기화
        gen_log = GenerationLog(
            session_id=session_id,
            source_image=str(image_path),
            item_type=item_type,
        )

        try:
            # 프롬프트 선택
            prompt = custom_prompt or self.PROMPTS.get(item_type, self.PROMPTS[ItemType.GRAPH])

            # 난이도 지시 추가
            difficulty_instruction = self._get_difficulty_instruction(difficulty)
            full_prompt = f"{prompt}\n\n{difficulty_instruction}"

            # Agentic Vision으로 이미지 분석 및 문항 생성
            result = self.vision_client.analyze_image_with_agentic_vision(
                image_path=image_path,
                prompt=full_prompt,
                enable_code_execution=True
            )

            # 단계 로그 추가
            gen_log.phases = self.vision_client.get_phase_logs()
            gen_log.total_duration_ms = result.get("total_duration_ms", 0)

            # 응답에서 문항 파싱
            item = self._parse_item_from_response(
                response_text=result.get("text", ""),
                item_type=item_type,
                difficulty=difficulty,
                image_path=str(image_path),
                evidence=self.vision_client.extract_evidence(result)
            )

            if item:
                gen_log.success = True
                gen_log.final_item_id = item.item_id
            else:
                gen_log.success = False

            self.generation_logs.append(gen_log)
            return item, gen_log

        except Exception as e:
            gen_log.success = False
            # 기존 로그가 있으면 사용, 없으면 빈 상태 유지
            phase_logs = self.vision_client.get_phase_logs()
            if phase_logs:
                gen_log.phases = phase_logs
            self.generation_logs.append(gen_log)
            raise RuntimeError(f"문항 생성 실패: {e}") from e

    def _get_difficulty_instruction(self, difficulty: DifficultyLevel) -> str:
        """난이도별 추가 지시문"""
        instructions = {
            DifficultyLevel.EASY: "**난이도: 쉬움** - 이미지에서 직접 읽을 수 있는 단순한 정보를 묻는 문항을 만드세요.",
            DifficultyLevel.MEDIUM: "**난이도: 보통** - 이미지 정보를 바탕으로 한 단계 추론이 필요한 문항을 만드세요.",
            DifficultyLevel.HARD: "**난이도: 어려움** - 이미지의 여러 정보를 종합하여 분석해야 하는 문항을 만드세요.",
        }
        return instructions.get(difficulty, instructions[DifficultyLevel.MEDIUM])

    def _parse_item_from_response(
        self,
        response_text: str,
        item_type: ItemType,
        difficulty: DifficultyLevel,
        image_path: str,
        evidence: EvidencePack
    ) -> Optional[ItemQuestion]:
        """응답 텍스트에서 문항 JSON 파싱

        v3.0.0: visual_spec 파싱 추가
        """
        try:
            # JSON 블록 추출
            json_str = self._extract_json_from_text(response_text)
            if not json_str:
                return None

            data = json.loads(json_str)

            # Choice 객체 생성
            choices = [
                Choice(label=c["label"], text=c["text"])
                for c in data.get("choices", [])
            ]

            if len(choices) < 2:
                return None

            # Evidence 업데이트
            evidence_facts = data.get("evidence_facts", [])
            evidence.extracted_facts.extend(evidence_facts)

            # v3.0.0: VisualSpec 파싱
            visual_spec = None
            if "visual_spec" in data and isinstance(data["visual_spec"], dict):
                vs_data = data["visual_spec"]
                visual_spec = VisualSpec(
                    required=vs_data.get("required", False),
                    image_prompt=vs_data.get("image_prompt", ""),
                    subject_context=vs_data.get("subject_context", ""),
                    style_guidance=vs_data.get("style_guidance", ""),
                    visual_type=vs_data.get("visual_type", ""),
                    description=vs_data.get("description", ""),
                )

            # 문항 생성
            item = ItemQuestion(
                item_id=f"ITEM-{uuid.uuid4().hex[:8].upper()}",
                item_type=item_type,
                difficulty=difficulty,
                stem=data.get("stem", ""),
                choices=choices,
                correct_answer=data.get("correct_answer", ""),
                explanation=data.get("explanation", ""),
                evidence=evidence,
                source_image=image_path,
                model_version=settings.gemini_model,
                visual_spec=visual_spec,
            )

            return item

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"문항 파싱 오류: {e}")
            return None

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """텍스트에서 JSON 블록 추출"""
        return extract_json_from_text(text)

    def generate_variation(
        self,
        original_item: QTIItem,
        variation_type: VariationType,
        image_path: Optional[str | Path] = None,
        item_type: Optional[ItemType] = None,
        difficulty: DifficultyLevel = DifficultyLevel.MEDIUM,
    ) -> tuple[Optional[ItemQuestion], GenerationLog]:
        """
        원본 문항 기반 변형 문항 생성

        Args:
            original_item: 원본 QTI 문항
            variation_type: 변형 유형 (similar, diff_up, diff_down, context, format)
            image_path: 이미지 경로 (있는 경우)
            item_type: 문항 유형
            difficulty: 목표 난이도

        Returns:
            (생성된 문항, 생성 로그) 튜플
        """
        session_id = str(uuid.uuid4())[:8]

        # 생성 로그 초기화
        gen_log = GenerationLog(
            session_id=session_id,
            source_image=str(image_path) if image_path else "",
            item_type=item_type or ItemType.GRAPH,
        )

        try:
            # 변형 프롬프트 템플릿 선택
            prompt_template = self.VARIATION_PROMPTS.get(variation_type)
            if not prompt_template:
                raise ValueError(f"지원하지 않는 변형 유형: {variation_type}")

            # 원본 문항 정보로 프롬프트 완성
            choices_text = "\n".join([f"  {c.label}. {c.text}" for c in original_item.choices])
            prompt = prompt_template.format(
                stem=original_item.stem,
                choices=choices_text,
                correct_answer=original_item.correct_answer,
                explanation=original_item.explanation,
            )

            # 이미지가 있으면 Agentic Vision 사용, 없으면 텍스트 기반
            if image_path:
                result = self.vision_client.analyze_image_with_agentic_vision(
                    image_path=Path(image_path),
                    prompt=prompt,
                    enable_code_execution=True
                )
            else:
                # 텍스트 전용 생성 (이미지 없이)
                result = self.vision_client.generate_text_only(prompt)

            # 단계 로그 추가
            gen_log.phases = self.vision_client.get_phase_logs()
            gen_log.total_duration_ms = result.get("total_duration_ms", 0)

            # 응답에서 문항 파싱
            evidence = EvidencePack()
            if image_path:
                evidence = self.vision_client.extract_evidence(result)

            item = self._parse_item_from_response(
                response_text=result.get("text", ""),
                item_type=item_type or ItemType.GRAPH,
                difficulty=difficulty,
                image_path=str(image_path) if image_path else "",
                evidence=evidence
            )

            if item:
                gen_log.success = True
                gen_log.final_item_id = item.item_id
            else:
                gen_log.success = False

            self.generation_logs.append(gen_log)
            return item, gen_log

        except Exception as e:
            gen_log.success = False
            self.generation_logs.append(gen_log)
            raise RuntimeError(f"변형 문항 생성 실패: {e}") from e

    def save_item(self, item: ItemQuestion, output_dir: Optional[Path] = None) -> Path:
        """문항을 JSON 파일로 저장"""
        output_dir = output_dir or settings.output_dir / "items"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{item.item_id}.json"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(item.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

        return filepath

    def save_log(self, log: GenerationLog, output_dir: Optional[Path] = None) -> Path:
        """생성 로그를 JSON 파일로 저장"""
        output_dir = output_dir or settings.output_dir / "logs"
        output_dir.mkdir(parents=True, exist_ok=True)

        filename = f"log-{log.session_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        filepath = output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(log.model_dump(mode="json"), f, ensure_ascii=False, indent=2, default=str)

        return filepath
