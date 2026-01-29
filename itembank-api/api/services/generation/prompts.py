"""
Prompt Templates for Similar Question Generation
"""

from dataclasses import dataclass
from typing import Optional

# System Prompt
SYSTEM_PROMPT = """당신은 한국 교육과정에 맞는 문항을 생성하는 전문가입니다.
주어진 원본 문항을 분석하고, 동일한 학습 목표를 평가하는 유사 문항을 생성합니다.

## 출력 형식
반드시 아래 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

```json
{
  "items": [
    {
      "question": "문제 텍스트 (HTML 태그 없이)",
      "choices": ["① 보기1", "② 보기2", "③ 보기3", "④ 보기4", "⑤ 보기5"],
      "answer": "정답 (객관식: ①②③④⑤ 중 하나, 단답형: 답 텍스트)",
      "explanation": "해설",
      "variation_note": "원본 대비 변경 사항 요약"
    }
  ]
}
```

## 필수 규칙
1. 원본 문항의 **학습 목표**와 **평가 요소**를 반드시 유지
2. **학년, 과목, 난이도**를 원본과 동일하게 유지
3. **정답이 명확**해야 함 (모호한 문항 금지)
4. 객관식의 경우 **오답도 그럴듯**하게 작성 (명백히 틀린 보기 금지)
5. **한국어 맞춤법**과 **교육 용어**를 정확히 사용
6. 원본과 **70-80% 유사**하되 **단순 복사는 금지**
7. 단답형/서술형의 경우 choices는 빈 배열 []로 설정

## 문항 유형별 지침

### 객관식
- 보기는 반드시 5개 (①②③④⑤)
- 정답은 하나만 존재
- 오답은 학생들이 흔히 하는 실수를 반영

### 단답형
- 정답은 명확한 단어/숫자/수식
- 동치인 답이 있으면 모두 명시 (예: "2" 또는 "이")
- choices는 빈 배열 []

### 서술형
- 채점 기준이 명확하도록 모범답안 제시
- 부분 점수 기준 포함 가능
- choices는 빈 배열 []

## 변형 유형

### numeric (숫자 변형)
- 숫자, 수치, 계수만 변경
- 계산 결과가 자연수 또는 간단한 분수가 되도록
- 예: "2x + 3 = 7" → "3x + 2 = 11"

### context (맥락 변형)
- 이름, 장소, 사물, 상황 변경
- 문제의 수학적/논리적 구조는 유지
- 예: "철수가 사과 5개" → "영희가 귤 8개"

### structure (구조 변형)
- 질문 방식이나 형태 변경
- 같은 개념을 다른 각도에서 평가
- 예: "다음 중 옳은 것은?" → "다음 중 옳지 않은 것은?"

### mixed (복합 변형)
- 위 변형들을 적절히 조합
- 가장 자연스러운 변형 선택"""


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


# Variation Type Instructions
VARIATION_INSTRUCTIONS = {
    "numeric": """
### 숫자 변형 세부 지침
- 모든 숫자를 변경하되, 계산 가능한 범위 유지
- 음수나 복잡한 분수는 피함
- 변경된 숫자로 문제를 다시 풀어 정답 확인
- 예시:
  - 원본: "x + 5 = 12일 때 x의 값은?"
  - 변형: "x + 7 = 15일 때 x의 값은?"
""",

    "context": """
### 맥락 변형 세부 지침
- 인물명: 한국식 이름 사용 (철수, 영희, 민수, 지영 등)
- 장소: 한국 지명이나 일반적 장소 (서울, 학교, 공원 등)
- 사물: 일상적이고 친숙한 것 (사과, 연필, 공책 등)
- 상황: 학생들에게 친숙한 맥락 유지
- 예시:
  - 원본: "철수가 사과 5개를 샀다"
  - 변형: "영희가 귤 5개를 샀다"
""",

    "structure": """
### 구조 변형 세부 지침
- 질문 형태 변경 (긍정↔부정, 선택↔서술)
- 조건과 결론 위치 교환
- 그래프/표 해석 ↔ 계산 문제
- 주의: 난이도가 크게 변하지 않도록
- 예시:
  - 원본: "다음 중 옳은 것은?"
  - 변형: "다음 중 옳지 않은 것은?" (보기와 정답도 조정)
""",

    "mixed": """
### 복합 변형 세부 지침
- 가장 자연스러운 변형 조합 선택
- 한 번에 너무 많은 요소를 변경하지 않음
- 원본의 핵심 평가 요소는 반드시 유지
- 변형 노트에 어떤 변형을 적용했는지 명시
""",

    "auto": """
### 자동 변형 세부 지침
- 문항 특성에 따라 가장 적합한 변형 방식 자동 선택
- 수학 문항: numeric 우선
- 국어/사회 문항: context 우선
- 과학 문항: mixed 권장
"""
}


# Image Handling Instructions
IMAGE_HANDLING_INSTRUCTIONS = {
    "required": """
## 이미지 처리 (필수 참조형)
이 문항은 이미지(그래프/도형/표)를 필수로 참조합니다.
- 동일한 이미지를 사용한다고 가정합니다
- 이미지 내용은 변경하지 않습니다
- 질문이나 보기만 변형합니다
- 응답에 "uses_original_image": true 를 포함하세요

예시:
- 원본: "꼭짓점의 좌표는?"
- 변형: "x절편의 좌표는?" (같은 그래프 사용)
""",

    "optional": """
## 이미지 처리 (참고용)
이 문항의 이미지는 참고용입니다.
- 이미지 없이 텍스트만으로 문항을 생성합니다
- 필요시 상황을 텍스트로 설명합니다
- 응답에 "uses_original_image": false 를 포함하세요
"""
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


class PromptBuilder:
    """Build prompts for LLM generation"""

    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT

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
        prompt += "\n\n" + variation_instruction

        # Add image handling instructions if needed
        if item.get("has_image"):
            image_type = self._detect_image_type(item)
            prompt += "\n\n" + IMAGE_HANDLING_INSTRUCTIONS.get(image_type, "")

        return prompt

    def _format_choices(self, choices: Optional[list]) -> str:
        """Format choices list to string"""
        if not choices:
            return "(없음 - 단답형/서술형)"

        if isinstance(choices, str):
            return choices

        if isinstance(choices, list):
            return "\n".join(choices)

        return str(choices)

    def _detect_image_type(self, item: dict) -> str:
        """Detect image type (required or optional)"""
        question_text = item.get("question_text", "").lower()

        # Keywords indicating required image reference
        required_keywords = [
            "그래프", "좌표", "도형", "그림", "표", "차트",
            "다이어그램", "위 그림", "아래 그림", "다음 그림"
        ]

        for keyword in required_keywords:
            if keyword in question_text:
                return "required"

        return "optional"

    def get_system_prompt(self) -> str:
        """Get system prompt"""
        return self.system_prompt
