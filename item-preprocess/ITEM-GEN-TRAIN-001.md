# 문항생성모델 학습 설계문서

**문서 ID**: ITEM-GEN-TRAIN-001
**버전**: v1.1.0
**대상 시스템**: 교육 문항 생성 Agent 모델
**목적**: 성취기준·성취수준·출제의도를 입력받아 평가에 사용 가능한 문항을 생성하는 모델을 학습한다.

---

## 1. 모델 역할 정의

모델은 지식을 설명하는 모델이 아니라
출제의도를 만족하는 평가 문항을 구성하는 생성 모델이다.

### 입력 (ItemSpecLite)

```json
{
  "achievement_code": "string",
  "level": "A~E",
  "item_type": "string",
  "misconception": "string",
  "context_material": "optional"
}
```

### 출력 (Item)

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

## 2. 학습 목표

1. 구조화된 문항 생성 능력 확보
2. 성취기준 일치 문항 생성
3. 정답 유일성 보장
4. 난이도 수준 유지
5. 부적절 문항 생성 억제

---

## 3. 학습 데이터 구성

### 3.1 원천 데이터

출제의도 추출 파이프라인 결과:

* 문항
* 출제의도
* 거부사례

---

### 3.2 SFT 데이터

출제의도 → 문항 매핑 학습

```json
{
 "messages":[
  {"role":"user","content":"<ItemSpecLite>"},
  {"role":"assistant","content":"<Item JSON>"}
 ]
}
```

조건:

* confidence ≥ 0.80
* 단일 정답 문항만 사용

---

### 3.3 DPO 데이터

좋은 문항 vs 나쁜 문항 비교 학습

```json
{
 "prompt":"<ItemSpecLite>",
 "chosen":"<good item>",
 "rejected":"<bad item>"
}
```

나쁜 문항 유형:

* 성취기준 불일치
* 난이도 불일치
* 복수 정답
* 무효 선택지

---

### 3.4 Refine 데이터

```
초기 생성 → 평가모델 수정 → 수정문항 학습
```

---

## 4. 학습 단계

### Stage 1 — Format Learning (SFT)

목적:

* JSON 형식 안정화
* 문항 기본 구조 학습

---

### Stage 2 — Alignment Learning (DPO)

목적:

* 교육적 타당성 확보
* 오류 생성 억제

---

### Stage 3 — Calibration (Refine)

목적:

* 난이도 안정화
* 품질 분산 감소

---

## 5. 학습 파라미터

| 항목         | 값           |
| ---------- | ----------- |
| 튜닝 방식      | LoRA / PEFT |
| Rank       | 16~32       |
| SFT lr     | 2e-4        |
| DPO lr     | 5e-5        |
| Refine lr  | 1e-5        |
| Epoch      | 2~3         |
| Max Length | 2048        |

---

## 6. 입력 템플릿 규격

### Generation Template

```
출제의도를 기반으로 시험 문항을 생성하라.
JSON 형식만 출력하라.
```

### Output Schema

```json
{
  "stem": "",
  "choices": [],
  "answer": "",
  "explanation": "",
  "quality_flags": []
}
```

---

## 7. 평가 방법

| 항목               | 기준    |
| ---------------- | ----- |
| JSON Valid Rate  | ≥ 99% |
| Intent Match     | ≥ 85% |
| Difficulty Hit@2 | ≥ 80% |
| Reject Rate      | ≥ 90% |
| Unique Rate      | ≥ 70% |

---

## 8. 데이터 사용 정책

| 판정        | 사용     |
| --------- | ------ |
| PASS      | SFT    |
| SOFT_PASS | Refine |
| FAIL      | DPO    |

---

## 9. 실패 대응

| 문제       | 대응        |
| -------- | --------- |
| 형식 오류    | 스키마 강화    |
| 난이도 붕괴   | Refine 증가 |
| 유사 문항 반복 | DPO 증가    |
| 정답 오류    | Reject 확대 |

---

## 10. 운영 루프

```
생성 → 평가 → 데이터 추가 → 재학습
```

모델은 반복 학습으로 품질이 향상된다.

---

**끝**
