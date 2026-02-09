# 문항 생성 파이프라인 문서 인덱스

AI 기반 문항 생성 시스템 파이프라인 명세 문서 모음

**버전**: v1.2.0
**수정일**: 2026-02-02

---

## 문서 구성

| 문서 | 설명 |
|------|------|
| [ITEM-GEN-PIPELINE-SPEC.md](ITEM-GEN-PIPELINE-SPEC.md) | 파이프라인 핵심 명세 (개요) |
| [P1-INPUT-SPEC.md](P1-INPUT-SPEC.md) | 입력 처리 단계 상세 |
| [P2-ANALYZE-SPEC.md](P2-ANALYZE-SPEC.md) | 분석 단계 상세 (AG-VIS) |
| [P3-GENERATE-SPEC.md](P3-GENERATE-SPEC.md) | 생성 단계 상세 (AG-GEN) |
| [P4-VALIDATE-SPEC.md](P4-VALIDATE-SPEC.md) | 검증 단계 상세 (AG-VAL, AG-CALC, AG-FACT, AG-SAFE) |
| [P5-OUTPUT-SPEC.md](P5-OUTPUT-SPEC.md) | 출력 단계 상세 (AG-IMG, AG-STD, AG-AUD) |

---

## 파이프라인 개요

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ P1-INPUT │───▶│P2-ANALYZE│───▶│P3-GENERATE│───▶│P4-VALIDATE│───▶│ P5-OUTPUT│
│          │    │          │    │          │    │          │    │          │
│ QTI/IML  │    │ Vision   │    │ 문항     │    │ 정답     │    │ 이미지   │
│ 파싱     │    │ 분석     │    │ 생성     │    │ 검증     │    │ 생성     │
│ 위치추출 │    │ 수치추출 │    │ 수치변형 │    │ 계산검증 │    │ 위치배치 │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
 InputPack      EvidencePack     DraftItem    ValidationReport  FinalItem
 (위치정보)                      (이미지스펙)                   (새이미지)
```

---

## 입력 시나리오

| 시나리오 | 입력 | 설명 | P2 | P3 | P5 |
|---------|------|------|:--:|:--:|:--:|
| **A** | 이미지만 | 신규 문항 생성 | ✅ | ✅ | 선택 |
| **B** | 원본+이미지 | 유사/변형 문항 ⭐ | ✅ | ✅ | ✅ |
| **C** | 원본만 | 텍스트 변형 | - | ✅ | - |

---

## 변형 유형

| 유형 | 코드 | 설명 | 예시 |
|------|------|------|------|
| 유사 | `similar` | 수치만 변경 | 85점→78점 |
| 난이도↑ | `diff_up` | 복잡도 증가 | 2변수→3변수 |
| 난이도↓ | `diff_down` | 단순화 | 연립→일차 |
| 신규 | `new` | 완전 새 문항 | - |

---

## 지원 과목

| 과목 | 이미지 유형 | 특수 검증 |
|------|------------|----------|
| **국어** | 지문, 도표 | AG-SAFE |
| **영어** | 지문, 도표, 그림 | AG-SAFE |
| **수학** | 그래프, 도형, 수식 | AG-CALC |
| **과학** | 실험도표, 그래프 | AG-CALC |
| **역사** | 지도, 연표, 사료 | AG-FACT, AG-SAFE |
| **사회** | 지도, 통계그래프 | AG-FACT, AG-SAFE |

---

## 에이전트 매트릭스

| 에이전트 | 역할 | 사용 모델 | 적용 단계 |
|---------|------|----------|----------|
| AG-VIS | Vision 분석 | Gemini 3 Flash | P2 |
| AG-GEN | 문항 생성 | Gemini 3 Flash | P3 |
| AG-VAL | 기본 검증 | Gemini 3 Flash | P4 |
| AG-IMG | 이미지 정합성 검증 | Gemini 3 Flash (Vision) | P4 |
| AG-CALC | 계산 검증 | Code Execution | P4 |
| AG-FACT | 사실 검증 | 외부 API | P4 |
| AG-SAFE | 안전 검증 | Gemini 3 Flash | P4 |
| AG-IMG | 이미지 생성 | Nano Banana Pro | P5 |
| AG-STD | 표준화 | 규칙 기반 | P5 |
| AG-AUD | 감사 로깅 | - | 전체 |

---

## 과목별 에이전트 조합

| 과목 | P2 | P3 | P4 | P5 |
|------|----|----|----|----|
| **국어** | AG-VIS | AG-GEN | AG-VAL, **AG-IMG**, AG-SAFE | AG-IMG, AG-STD |
| **영어** | AG-VIS | AG-GEN | AG-VAL, **AG-IMG**, AG-SAFE | AG-IMG, AG-STD |
| **수학** | AG-VIS | AG-GEN | AG-VAL, **AG-IMG**, AG-CALC | AG-IMG, AG-STD |
| **과학** | AG-VIS | AG-GEN | AG-VAL, **AG-IMG**, AG-CALC | AG-IMG, AG-STD |
| **역사** | AG-VIS | AG-GEN | AG-VAL, **AG-IMG**, AG-FACT, AG-SAFE | AG-IMG, AG-STD |
| **사회** | AG-VIS | AG-GEN | AG-VAL, **AG-IMG**, AG-FACT, AG-SAFE | AG-IMG, AG-STD |

> **AG-IMG (P4)**: 이미지 포함 문항에만 적용 - 이미지-문항 정합성 검증

---

## 이미지 위치 보존

```
[P1] 원본 위치 추출
      ↓
[P3] 새 문항에 위치 정보 포함
      ↓
[P5] 원본 위치에 새 이미지 배치
```

| 위치 코드 | 설명 |
|----------|------|
| `before_stem` | 문제 앞 |
| `after_stem` | 문제 뒤 |
| `inline` | 문장 내 |
| `in_choice` | 선지 내 |

---

## 검증 레벨

| 레벨 | 모델 수 | 사용 모델 | 적용 상황 |
|------|--------|----------|----------|
| Level 1 | 1 | Gemini Flash | 수학, 과학 |
| Level 2 | 2 | + GPT-4o | 역사, 사회 |
| Level 3 | 3 | + Gemini Pro | 민감 주제 |
| Level 4 | 3+ | + 전문가 검토 | 공식 시험 |

---

## 오류 코드

| 코드 | 단계 | 의미 | 처리 |
|------|------|------|------|
| E001 | P1 | 입력 파싱 실패 | 요청 반려 |
| E002 | P2 | Vision 분석 실패 | 재시도 (3회) |
| E003 | P3 | 생성 실패 | 재시도 (3회) |
| E004 | P4 | 계산 검증 실패 | 재생성 |
| E005 | P4 | 사실 검증 실패 | 즉시 폐기 |
| E006 | P4 | 편향/안전 위반 | 전문가 검토 |
| E007 | P5 | 이미지 생성 실패 | 텍스트 전용 |
| E008 | P5 | 위치 보존 실패 | 기본 위치 |
| E009 | ALL | 타임아웃 | 재시도 (3회) |

---

## 성능 목표

| 지표 | 이미지 없음 | 이미지 포함 |
|------|-----------|-----------|
| 단일 문항 | < 30초 | < 90초 |
| 배치 처리 | 120문항/시간 | 40문항/시간 |

---

## 구현 현황

### Phase 1: Core ✅
- [x] P1 입력 파서 (IML 지원)
- [x] P2 AG-VIS 구현
- [x] P3 AG-GEN 구현
- [x] 기본 출력 포맷터

### Phase 2: Validation ⚠️
- [x] P4 AG-VAL 구현
- [ ] AG-CALC (Code Execution)
- [ ] AG-FACT (외부 API 연동)
- [ ] AG-SAFE (안전 검증)

### Phase 3: Output ⚠️
- [x] P5 AG-IMG (Nano Banana Pro)
- [ ] AG-STD (표준화)
- [x] AG-AUD (감사 로깅) - 부분

### Phase 4: Production
- [ ] API 엔드포인트
- [ ] 배치 처리
- [ ] 모니터링/대시보드

---

**마지막 업데이트**: 2026-02-02
