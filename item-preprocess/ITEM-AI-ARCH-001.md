# 통합 시스템 아키텍처 설계문서

**문서 ID**: ITEM-AI-ARCH-001
**버전**: v1.0.0
**대상 시스템**: 교육 문항 생성·검증·학습 자동화 Agent 플랫폼
**운영 방식**: 온프레미스 멀티에이전트 협업 구조

---

## 1. 목적

본 시스템은 교육과정 기반 문항 생성, 품질 검증, 데이터 축적, 모델 재학습을 자동으로 수행하는 평가 콘텐츠 생성 플랫폼을 구축하는 것을 목적으로 한다.

시스템은 단일 모델이 아닌 역할 분리된 에이전트들이 협력하여 동작하며, 반복 학습을 통해 품질을 향상시킨다.

---

## 2. 아키텍처 개요

시스템은 입력 문항 처리, 출제의도 분석, 문항 생성, 품질 판정, 데이터 생성, 재학습의 순환 구조를 가진다.

```
QTI Input
   ↓
Ingest Agent
   ↓
Vision Router
   ↓
Vision Parser
   ↓
Intent Agent
   ↓
Generate Agent
   ↓
Evaluate Agent
   ↓
Data Builder
   ↓
Trainer
   ↓
Model Registry
```

---

## 3. 에이전트 구성

### 3.1 Ingest Agent

역할:

* QTI 문항 파싱
* 내부 공통 스키마 변환
* 자산(이미지) 추출

출력: InternalItemSchema

---

### 3.2 Vision Router

역할:

* 이미지 필요 여부 판단
* Essential / Support / Decorative 분류

규칙:

* 그래프/표/도형 포함 시 Essential
* 단순 삽화는 Decorative

---

### 3.3 Vision Parser Agent

역할:

* 이미지 → 구조화 JSON 변환
* OCR 및 시각 요소 추출

출력: Vision JSON

---

### 3.4 Intent Agent

역할:

* 성취기준 후보 탐색(RAG)
* 성취수준 추정
* 출제의도(ItemSpecLite) 생성

출력:

* achievement_topk
* level_topk
* intent_topk

---

### 3.5 Generate Agent

역할:

* 출제의도 기반 문항 생성
* 다중 후보 생성

출력: Candidate Items

---

### 3.6 Evaluate Agent

역할:

* 문항 품질 판정
* PASS / SOFT_PASS / FAIL 결정

평가 기준:

* 성취기준 일치
* 난이도 적합
* 정답 유일성
* 교육 타당성

---

### 3.7 Data Builder Agent

역할:

* 학습 데이터 생성

데이터 유형:

* SFT
* DPO
* Refine

---

### 3.8 Trainer Agent

역할:

* 모델 재학습 수행
* Generator / Judge 업데이트

---

### 3.9 Model Registry

역할:

* 모델 버전 관리
* 롤백 지원

---

## 4. 데이터 흐름

```
문항 → 구조화 → 의도 → 생성 → 평가 → 분류 → 학습 → 모델 업데이트
```

평가 결과에 따라 데이터가 구분된다.

| 판정        | 데이터 사용 |
| --------- | ------ |
| PASS      | SFT    |
| SOFT_PASS | Refine |
| FAIL      | DPO    |

---

## 5. 운영 모드

### Batch Mode

* 대량 문항 처리
* 데이터셋 구축 목적

### Online Mode

* 실시간 문항 생성
* 사용자 요청 처리

---

## 6. 안정성 설계

### Drift 감지

이전 모델 대비 주요 지표 비교 후 배포

### Rollback

성능 저하 시 이전 버전 복원

---

## 7. 확장성

| 확장 항목    | 방법                  |
| -------- | ------------------- |
| 과목 추가    | 템플릿 확장              |
| 문항 유형 추가 | Prompt 확장           |
| 평가 기준 변경 | Evaluate Agent 업데이트 |

---

## 8. 시스템 특성

* 다중 에이전트 협업 구조
* 자동 학습 루프
* 온프레미스 운영
* 모델 교체 가능 구조

---

**끝**
