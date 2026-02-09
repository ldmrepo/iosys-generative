# 프롬프트 인터페이스 규격

**문서 ID**: ITEM-PROMPT-SPEC-001
**버전**: v1.1.0
**대상 시스템**: 문항 생성 및 평가 LLM 인터페이스
**목적**: 학습·추론·평가 전 과정에서 동일한 입력 형식을 사용하여 모델 동작의 재현성과 안정성을 확보한다.

---

## 1. 기본 원칙

1. 모든 모델 호출은 정의된 템플릿을 사용한다.
2. 자유 형식 입력을 금지한다.
3. JSON 출력만 허용한다.
4. 학습·추론·평가 입력 형식은 동일하게 유지한다.

---

## 2. 공통 입력 데이터 구조

### ItemSpecLite

```json
{
  "achievement_code": "string",
  "level": "A|B|C|D|E",
  "item_type": "string",
  "misconception": "string",
  "context_material": "optional"
}
```

### Item

```json
{
  "stem": "string",
  "choices": ["string"],
  "answer": "string",
  "explanation": "string",
  "quality_flags": []
}
```

---

## 3. 문항 생성 템플릿

### Generation Template v1

```
[System]
당신은 교육 평가 전문가이다.
출제의도를 만족하는 시험 문항을 작성하라.
설명 없이 JSON만 출력하라.

[User]
출제의도:
{ItemSpecLite}

조건:
- 정답은 하나여야 한다
- 난이도는 level과 일치해야 한다
- 오개념이 선택지에 포함되어야 한다
```

### 출력 규격

```json
{
  "stem": "",
  "choices": ["", "", "", ""],
  "answer": "",
  "explanation": "",
  "quality_flags": []
}
```

---

## 4. 평가 템플릿

### Evaluation Template v1

```
[System]
문항의 품질을 평가하라.

[User]
출제의도:
{ItemSpecLite}

문항:
{Item}

다음 항목을 판단하라:
- 성취기준 일치
- 난이도 적합
- 정답 유일성
- 교육 타당성

JSON으로 출력하라.
```

### 출력 규격

```json
{
  "verdict": "PASS|SOFT_PASS|FAIL",
  "scores": {
    "intent_match": 0.0,
    "difficulty_match": 0.0,
    "answer_validity": 0.0,
    "pedagogical_quality": 0.0
  },
  "reasons": []
}
```

---

## 5. 거부 테스트 템플릿

### Rejection Template v1

```
출제의도에 더 적합한 문항을 선택하라.

출제의도:
{ItemSpecLite}

A:
{ItemA}

B:
{ItemB}
```

### 출력

```json
{
  "chosen": "A|B"
}
```

---

## 6. 의도 추출 템플릿

### Intent Extraction Template v1

```
문항의 출제의도를 추출하라.

문항:
{ItemText}

가능한 성취기준 후보와 난이도를 JSON으로 출력하라.
```

### 출력

```json
{
  "achievement_topk": [],
  "level_topk": [],
  "intent_topk": []
}
```

---

## 7. 템플릿 사용 규칙

| 영역 | 템플릿 |
| -- | --- |
| 학습 | 동일  |
| 추론 | 동일  |
| 평가 | 동일  |

템플릿 변경 시 모델 재학습이 필요하다.

---

## 8. 오류 처리

| 상황        | 처리      |
| --------- | ------- |
| 비 JSON 출력 | 재시도     |
| 필드 누락     | FAIL 처리 |
| 추가 텍스트 포함 | 무효 처리   |

---

**끝**
