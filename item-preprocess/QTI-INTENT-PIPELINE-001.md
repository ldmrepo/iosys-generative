# QTI 기반 출제의도 추출 파이프라인 설계문서

**문서 ID**: QTI-INTENT-PIPELINE-001
**버전**: v1.0.0
**대상 시스템**: 교육 문항 생성·검증·학습 자동화 Agent 플랫폼
**목적**: QTI 형식 문항으로부터 성취기준, 성취수준, 출제의도 및 거부사례를 자동 생성하여 학습 데이터셋을 구축한다.

---

## 1. 입력 정의

### 1.1 입력 데이터

* QTI Item(XML/패키지)

  * stem
  * choices
  * correctResponse
  * feedback(optional)
  * interactionType
  * asset(image)

### 1.2 참조 데이터

* 교육과정 성취기준 텍스트
* 성취수준 정의
* 문항 유형 규칙

---

## 2. 출력 정의

### 2.1 기본 출력

```json
{
  "achievement_topk": [],
  "level_topk": [],
  "intent_topk": [],
  "confidence": 0.0
}
```

### 2.2 학습용 출력

```json
{
  "sft": {},
  "dpo": {},
  "trace": {}
}
```

---

## 3. 처리 단계

### Step 1 — QTI Normalize

역할:

* QTI 구조를 내부 공통 스키마로 변환
* 이미지 경로 추출

출력:
InternalItemSchema

---

### Step 2 — Vision Router

역할:

* 이미지 필요성 판단

분류:

* Essential: 정답 판단에 필요
* Support: 보조 정보
* Decorative: 의미 없음

규칙:

* 그래프/표/도형 포함 시 Essential
* 설명 삽화는 Decorative

---

### Step 3 — Vision Parsing

조건:
Essential일 때만 수행

역할:

* 이미지 구조화
* 텍스트 추출(OCR)
* 시각 관계 추출

출력:
Vision JSON

```json
{
  "type": "",
  "caption": "",
  "structured": {}
}
```

---

### Step 4 — Curriculum Retrieval (RAG)

역할:

* 문항 텍스트 + Vision JSON으로 성취기준 후보 검색

출력:
achievement_topk

---

### Step 5 — Intent Generation

역할:

* 성취기준/수준/문항유형/오개념 추출

출력:
intent_topk

구조:

```json
{
  "achievement_code": "",
  "level": "",
  "item_type": "",
  "misconception": ""
}
```

---

### Step 6 — Verification

역할:

* 근거 기반 검증
* PASS / SOFT_PASS / FAIL 판정

---

### Step 7 — Reject Builder

역할:

* 거부사례 생성

방법:

* 인접 성취기준 교란
* 난이도 교란
* 유형 교란

출력:
DPO 데이터

---

## 4. 신뢰도 정책

| 조건                | 처리        |
| ----------------- | --------- |
| confidence ≥ 0.80 | SFT + DPO |
| 0.60~0.79         | DPO만      |
| < 0.60            | 폐기        |

---

## 5. 데이터 저장

저장 형식: JSONL

레코드 구성:

* normalized_item
* vision_json(optional)
* intent_topk
* judge_result
* dpo_pairs
* trace_log

---

## 6. 실패 처리

| 상황        | 대응               |
| --------- | ---------------- |
| Vision 실패 | TEXT 모드 fallback |
| RAG 실패    | UNKNOWN 처리       |
| Judge 불일치 | Hard case 저장     |

---

## 7. 파이프라인 특성

* 이미지 선택적 처리
* Top-K 라벨 생성
* 자동 거부사례 생성
* 학습 데이터 직접 생성 가능

---

**끝**
