"""
Prompt Templates for Similar Question Generation
"""

from dataclasses import dataclass
from typing import Optional

# System Prompt
SYSTEM_PROMPT_BASE = """당신은 한국 교육과정에 맞는 문항을 생성하는 전문가입니다.
주어진 원본 문항을 분석하고, 동일한 학습 목표를 평가하는 유사 문항을 생성합니다.

중요: 반드시 유효한 JSON만 출력하세요. 설명 텍스트나 마크다운 코드블록 없이 순수 JSON만 응답하세요.

출력 형식:
{"items":[{"question":"문제 텍스트","choices":["1번","2번","3번","4번","5번"],"correct_choice":1,"explanation":"해설","variation_note":"변경사항"}]}

규칙:
- question: 문제 텍스트 (수식은 TeX 형식, 예: x^2, \\frac{1}{2})
- choices: 5개 선택지 배열 (객관식) 또는 빈 배열 (단답형)
- correct_choice: 정답 번호 1-5 (객관식) 또는 0 (단답형)
- explanation: 간단한 해설
- variation_note: 원본 대비 변경 사항 요약

필수:
- 원본과 동일한 학습목표, 난이도, 과목 유지
- 숫자/맥락/구조 변형으로 유사문항 생성
- JSON 문자열 내 큰따옴표는 \\"로 이스케이프"""


# Vision-specific System Prompt Extension
SYSTEM_PROMPT_VISION_EXT = """

## 이미지 문항 생성 지침

이미지가 첨부된 문항입니다.

### 규칙
1. **이미지 없이 풀 수 있는 문항 생성**
   - 이미지의 수치/조건을 텍스트로 명시
   - 새로운 수치로 유사한 구조의 문제 생성

2. 이미지에 없는 정보를 만들어내지 마세요"""


# User Prompt Template
USER_PROMPT_TEMPLATE = """## 원본 문항

**과목**: {subject}
**학년**: {grade}
**난이도**: {difficulty}
**문항유형**: {question_type}
**단원**: {unit}

**문제**:
{question_text}

**보기**:
{choices}

**정답**: {answer}

**해설**:
{explanation}

---

## 생성 요청

- **생성 개수**: {count}개
- **변형 유형**: {variation_type}
- **추가 조건**: {additional_prompt}

위 원본 문항을 기반으로 {count}개의 유사 문항을 생성해주세요."""


# Vision-specific User Prompt Extension
USER_PROMPT_VISION_EXT = """

---

## 이미지 정보

이 문항에는 이미지가 포함되어 있습니다.
이미지 없이도 풀 수 있도록 모든 조건을 텍스트로 명시하세요."""


# Variation Type Instructions
VARIATION_INSTRUCTIONS = {
    "numeric": "\n### 숫자 변형: 모든 숫자를 변경하되 계산 가능한 범위 유지",
    "context": "\n### 맥락 변형: 이름, 장소, 사물 변경",
    "structure": "\n### 구조 변형: 질문 형태 변경",
    "mixed": "\n### 복합 변형: 적절히 조합",
    "auto": "\n### 자동: 문항에 적합한 변형 선택"
}


# Variation Type Names (Korean)
VARIATION_TYPE_NAMES = {
    "numeric": "숫자 변형",
    "context": "맥락 변형",
    "structure": "구조 변형",
    "mixed": "복합 변형",
    "auto": "자동 선택"
}


@dataclass
class GenerationRequest:
    """Generation request parameters"""
    source_item: dict
    count: int = 3
    variation_type: str = "mixed"
    additional_prompt: str = ""
    has_images: bool = False


class PromptBuilder:
    """Build prompts for LLM generation"""

    def __init__(self):
        pass

    def get_system_prompt(self, has_images: bool = False) -> str:
        """Get system prompt, with Vision extension if images are present"""
        if has_images:
            return SYSTEM_PROMPT_BASE + SYSTEM_PROMPT_VISION_EXT
        return SYSTEM_PROMPT_BASE

    def build_user_prompt(self, request: GenerationRequest) -> str:
        """Build user prompt from generation request"""
        item = request.source_item

        # Format choices
        choices_text = self._format_choices(item.get("choices"))

        # Build base prompt
        prompt = USER_PROMPT_TEMPLATE.format(
            subject=item.get("subject", "미지정"),
            grade=item.get("grade", "미지정"),
            difficulty=item.get("difficulty", "미지정"),
            question_type=item.get("question_type", "미지정"),
            unit=item.get("unit_large", "") or item.get("unit_medium", "") or "미지정",
            question_text=item.get("question_text", ""),
            choices=choices_text,
            answer=item.get("answer_text", ""),
            explanation=item.get("explanation_text", "") or "(해설 없음)",
            count=request.count,
            variation_type=VARIATION_TYPE_NAMES.get(request.variation_type, "복합 변형"),
            additional_prompt=request.additional_prompt or "(없음)"
        )

        # Add variation instructions
        variation_instruction = VARIATION_INSTRUCTIONS.get(
            request.variation_type,
            VARIATION_INSTRUCTIONS["mixed"]
        )
        prompt += variation_instruction

        # Add Vision-specific content if has images
        if request.has_images:
            prompt += USER_PROMPT_VISION_EXT

        return prompt

    def _format_choices(self, choices: Optional[list]) -> str:
        """Format choices list to string"""
        if not choices:
            return "(없음 - 단답형/서술형)"

        if isinstance(choices, str):
            return choices

        if isinstance(choices, list):
            return "\n".join(str(c) for c in choices)

        return str(choices)
