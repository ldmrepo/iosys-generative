# Gemini Agentic Vision 기반 AI 문항 생성 시스템 POC 계획서

**문서 ID**: POC-PLAN-001
**작성일**: 2026-02-01
**버전**: v1.0.0

---

## 1. 자료조사 요약

### 1.1 핵심 기술: Gemini 3 Flash Agentic Vision

| 항목 | 내용 |
|------|------|
| 발표일 | 2026년 1월 27일 (Google 공식 블로그) |
| 모델 | Gemini 3 Flash |
| 핵심 원리 | Think-Act-Observe 루프 기반 능동적 시각 탐색 |
| 성능 향상 | Vision 벤치마크 5~10% 품질 개선 |
| 활성화 방법 | `tools=["code_execution"]` 옵션 |

### 1.2 기술 동작 원리

```
Think (계획) → Act (실행) → Observe (관찰) → 최종 답변
```

1. **Think**: 이미지 분석 후 세부 탐색 필요 여부 판단
2. **Act**: Python 코드로 이미지 처리 (crop/rotate/zoom/annotate)
3. **Observe**: 실행 결과를 context window에 재투입하여 재추론

### 1.3 기존 문서 체계

| 문서 | 용도 |
|------|------|
| AV-ITEM-ARCH-001 | 단일 에이전트 아키텍처 명세 |
| AV-ITEM-MA-ARCH-001 | Multi-Agent 확장 아키텍처 |
| AV-ITEM-PROMPT-001 | 문항 유형별 프롬프트 패턴 |
| AV-ITEM-PIPELINE-001 | 출제-검수 통합 파이프라인 |

---

## 2. POC 목표

### 2.1 주요 목표

1. **Agentic Vision 기능 검증**: Gemini 3 Flash의 Think-Act-Observe 루프 동작 확인
2. **문항 생성 품질 평가**: 이미지 기반 객관식 문항 자동 생성 가능성 검증
3. **검수 자동화 가능성**: 문항-이미지 정합성 자동 검증 테스트
4. **Multi-Agent 확장성**: 역할 분리 에이전트 협업 구조 초기 구현

### 2.2 성공 기준

| 기준 | 목표치 |
|------|--------|
| 문항 생성 성공률 | 70% 이상 |
| 자동 검수 통과율 | 60% 이상 |
| 시각 근거 추적 가능 | 100% |
| Think-Act-Observe 로그 확보 | 100% |

---

## 3. POC 범위

### 3.1 포함 범위 (In Scope)

- Gemini 3 Flash API 연동
- 기본 이미지 유형 3종 테스트
  - 그래프 해석형
  - 도형/공간 인식형
  - 측정값 판독형
- 단일 에이전트 기반 문항 생성
- 기본 검수 로직 (정합성 검사)
- Think-Act-Observe 로그 수집

### 3.2 제외 범위 (Out of Scope)

- 전체 Multi-Agent 오케스트레이션 (Phase 2)
- 난이도 자동 조절 (Phase 2)
- 편향/안전성 필터링 (Phase 2)
- 대규모 배치 처리
- 프로덕션 배포

---

## 4. POC 아키텍처

### 4.1 단순화된 구조 (Phase 1)

```
[입력]
  ├─ 이미지 파일
  └─ 출제 조건 (유형, 난이도)
        │
        ▼
[Gemini 3 Flash + Agentic Vision]
  ├─ Think: 시각 분석 계획
  ├─ Act: 이미지 동적 탐색
  └─ Observe: 정보 추출
        │
        ▼
[문항 생성]
  ├─ 질문 생성
  ├─ 선지 생성
  ├─ 정답 및 해설
  └─ 시각 근거 기록
        │
        ▼
[기본 검수]
  ├─ 정합성 검사
  └─ 판별 가능성 확인
        │
        ▼
[출력]
  ├─ 문항 JSON
  ├─ Evidence Pack
  └─ 로그
```

### 4.2 핵심 컴포넌트

| 컴포넌트 | 기술 | 역할 |
|----------|------|------|
| API Client | Python + google.ai | Gemini API 호출 |
| Vision Module | Agentic Vision | 이미지 탐색/분석 |
| Item Generator | Prompt Engineering | 문항 생성 |
| Validator | Rule-based + AI | 기본 검수 |
| Logger | JSON/File | 로그 저장 |

---

## 5. 기술 스택

### 5.1 필수 기술

| 구분 | 기술 | 버전 |
|------|------|------|
| Language | Python | 3.11+ |
| AI API | Google AI (Gemini) | gemini-3-flash-preview |
| 이미지 처리 | Pillow | 10.x |
| 데이터 형식 | JSON | - |
| 로깅 | Python logging | - |

### 5.2 API 호출 예시

```python
from google.ai import genai

model = genai.GenerativeModel(
    model_name="models/gemini-3-flash-preview",
    tools=["code_execution"]
)

response = model.generate_content([
    prompt,
    image
])
```

---

## 6. 테스트 시나리오

### 6.1 그래프 해석형

**입력**: 막대/선 그래프 이미지
**프롬프트**:
```
이 이미지는 그래프이다.
필요하다면 특정 구간을 확대하여 수치를 정확히 확인하라.
그래프에서 직접 확인 가능한 정보만을 사용하여
객관식 문항 1개와 정답, 해설을 생성하라.
```
**기대 출력**: 그래프 수치 기반 문항

### 6.2 도형 인식형

**입력**: 기하 도형 이미지
**프롬프트**:
```
도형의 길이, 각도, 위치 관계를 분석하라.
필요 시 특정 부분을 확대하여 판단하라.
시각적 근거가 명확한 조건만을 사용하여 문항을 구성하라.
```
**기대 출력**: 도형 속성 기반 문항

### 6.3 측정값 판독형

**입력**: 측정 기기/눈금 이미지
**프롬프트**:
```
이미지에 포함된 측정 기기와 수치를 분석하라.
판독이 어려운 경우 해당 영역을 확대하라.
이미지로 검증 가능한 측정값만을 사용하여
개념 이해를 평가하는 문항을 생성하라.
```
**기대 출력**: 측정값 기반 문항

---

## 7. 산출물 스키마

### 7.1 문항 JSON 스키마

```json
{
  "item_id": "string",
  "item_type": "multiple_choice",
  "stem": "문항 질문",
  "choices": [
    {"label": "A", "text": "선지1"},
    {"label": "B", "text": "선지2"},
    {"label": "C", "text": "선지3"},
    {"label": "D", "text": "선지4"}
  ],
  "correct_answer": "A",
  "explanation": "해설",
  "evidence": {
    "regions": [...],
    "extracted_facts": [...]
  },
  "metadata": {
    "source_image": "path",
    "generated_at": "timestamp",
    "model_version": "gemini-3-flash-preview"
  }
}
```

### 7.2 로그 스키마

```json
{
  "session_id": "string",
  "timestamp": "ISO8601",
  "phase": "think|act|observe",
  "input": {...},
  "output": {...},
  "code_executed": "string|null",
  "duration_ms": 0
}
```

---

## 8. 일정 계획

### Phase 1: 기초 구현 (1주차)

| 일차 | 작업 |
|------|------|
| Day 1-2 | 환경 설정, API 연동, 기본 호출 테스트 |
| Day 3-4 | 프롬프트 템플릿 구현, 이미지 유형별 테스트 |
| Day 5 | 출력 파서, JSON 스키마 적용 |

### Phase 2: 검수 및 로깅 (2주차)

| 일차 | 작업 |
|------|------|
| Day 6-7 | 기본 검수 로직 구현 |
| Day 8-9 | Think-Act-Observe 로그 수집 구현 |
| Day 10 | 통합 테스트, 결과 분석 |

---

## 9. 리스크 및 대응

| 리스크 | 영향 | 대응 방안 |
|--------|------|-----------|
| API 접근 제한 | 높음 | Preview 액세스 사전 신청 |
| 이미지 해상도 문제 | 중간 | 전처리 로직 추가 |
| 토큰 비용 초과 | 중간 | 호출 횟수 제한, 캐싱 |
| 문항 품질 미달 | 중간 | 프롬프트 반복 개선 |

---

## 10. 다음 단계 (Phase 2 예고)

POC 완료 후 Multi-Agent 아키텍처 확장:

1. **AG-ORCH**: 오케스트레이터 구현
2. **AG-VIS + AG-GEN**: 역할 분리
3. **AG-VAL**: 전문 검수 에이전트
4. **AG-DIFF**: 난이도 조절
5. **AG-SAFE**: 편향/안전성 필터

---

## 11. 체크리스트

### 시작 전 준비

- [ ] Google AI API 키 발급
- [ ] Gemini 3 Flash Preview 액세스 확인
- [ ] Python 환경 구성
- [ ] 테스트 이미지 셋 준비 (각 유형별 5개 이상)

### POC 완료 기준

- [ ] 3개 이미지 유형 테스트 완료
- [ ] 문항 생성 성공률 70% 달성
- [ ] Think-Act-Observe 로그 확보
- [ ] 결과 분석 보고서 작성

---

## 참고 문서

- tech.md: 최신 기술 동향
- AV-ITEM-ARCH-001.md: 아키텍처 명세
- AV-ITEM-PROMPT-001.md: 프롬프트 패턴
- AV-ITEM-PIPELINE-001.md: 파이프라인 설계
- AV-ITEM-MA-ARCH-001.md: Multi-Agent 설계
