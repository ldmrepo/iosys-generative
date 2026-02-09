# P4-VALIDATE 단계 명세

**문서 ID**: P4-VALIDATE-SPEC-001
**버전**: v1.4.0
**수정일**: 2026-02-02
**목적**: 문항 검증 단계 상세 명세

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| **단계** | P4-VALIDATE |
| **에이전트** | AG-VAL, AG-IMG, AG-CALC, AG-FACT, AG-SAFE |
| **입력** | `DraftItem` + `EvidencePack` |
| **출력** | `ValidationReport` |
| **목표 시간** | Level 1: 5~10초, Level 2+: 15~30초 |

### 1.1 구현 현황

| 에이전트 | 상태 | 구현 클래스 | 비고 |
|---------|:----:|------------|------|
| AG-VAL | ⚠️ | `QualityChecker` | 규칙 기반 (LLM 보완 예정) |
| AG-IMG | ✅ | `ConsistencyValidator` | Gemini Vision 기반 |
| AG-CALC | ❌ | - | Phase 2 예정 |
| AG-FACT | ❌ | - | Phase 2 예정 |
| AG-SAFE | ❌ | - | Phase 2 예정 |

---

## 2. 검증 에이전트

### 2.1 AG-VAL (Core Validator)

- 기본 검증 수행
- 정답 유일성, 선택지 구분성
- 난이도/교육과정 부합성
- **모든 과목에 적용**

### 2.2 AG-IMG (Image Consistency Validator) ⭐

- **이미지-문항 정합성 검증**
- Gemini Vision 기반 시각 분석
- 문항이 이미지 내용과 일치하는지 검증
- 정답이 이미지에서 도출 가능한지 확인
- **이미지 포함 문항에 적용** (모든 과목)

### 2.3 AG-CALC (Calculation Verifier) - Phase 2

- 수학/과학 계산 검증
- **Code Execution** 활용 (샌드박스 환경)
- Python + SymPy 기반
- **적용 과목**: 수학, 과학
- **구현 예정**: Phase 2 (보안 샌드박스 필요)

### 2.4 AG-FACT (Fact Checker) - Phase 2

- 역사/사회 사실 검증
- 외부 데이터 소스:
  - **Wikipedia API** (1차) - 무료, 한국어 지원
  - 통계청 KOSIS API (2차) - API 키 필요
  - LLM 기반 사실 확인 (보조)
- **적용 과목**: 역사, 사회
- **구현 예정**: Phase 2

### 2.5 AG-SAFE (Safety Checker) - Phase 2

- 편향 검사 (성별, 인종, 지역 등)
- 유해 콘텐츠 탐지
- 민감 주제 검토
- **적용 과목**: 국어, 영어, 역사, 사회
- **구현 예정**: Phase 2 (LLM 프롬프트 기반, 구현 난이도 낮음)

---

## 3. 과목별 에이전트 조합 ⭐

| 과목 | AG-VAL | AG-IMG | AG-CALC | AG-FACT | AG-SAFE |
|------|:------:|:------:|:-------:|:-------:|:-------:|
| **국어** | ✅ | ⭐ | - | - | ✅ |
| **영어** | ✅ | ⭐ | - | - | ✅ |
| **수학** | ✅ | ⭐ | ✅ | - | - |
| **과학** | ✅ | ⭐ | ✅ | - | - |
| **역사** | ✅ | ⭐ | - | ✅ | ✅ |
| **사회** | ✅ | ⭐ | - | ✅ | ✅ |

> ⭐ AG-IMG는 이미지 포함 문항에만 적용

---

## 4. 출력: ValidationReport

```python
@dataclass
class ValidationReport:
    item_id: str
    overall_status: str        # PASS | FAIL | HOLD
    checks: List[CheckResult]  # 개별 검증 결과
    score: float               # 0.0 ~ 1.0
    issues: List[Issue]        # 발견된 이슈
    recommendations: List[str] # 개선 권고
    cross_validation: dict     # 교차 검증 결과
    agents_used: List[str]     # ⭐ 사용된 에이전트 목록
```

### 4.1 CheckResult

```python
@dataclass
class CheckResult:
    check_code: str      # 검증 코드
    status: str          # PASS | FAIL | WARN
    message: str         # 결과 메시지
    evidence: str        # 검증 근거
    weight: float        # 가중치
    agent: str           # ⭐ 검증 수행 에이전트
```

---

## 5. 검증 체크리스트

### 5.1 공통 검증 (AG-VAL)

| 코드 | 검증 항목 | 가중치 | 실패 시 처리 |
|------|----------|--------|-------------|
| `ANS_UNIQUE` | 정답 유일성 | 1.0 | 재생성 |
| `ANS_CORRECT` | 정답 정확성 | 1.0 | 재생성 |
| `OPT_DISTINCT` | 선택지 구분성 | 0.8 | 재생성 |
| `OPT_PLAUSIBLE` | 오답 타당성 | 0.7 | 경고 |
| `DIFF_MATCH` | 난이도 부합 | 0.6 | 경고 |
| `CURR_ALIGN` | 교육과정 부합 | 0.8 | 경고 |

### 5.2 이미지 정합성 검증 (AG-IMG) - 이미지 포함 문항 ⭐

| 코드 | 검증 항목 | 가중치 | 실패 시 처리 |
|------|----------|--------|-------------|
| `IMG_QUESTION_MATCH` | 문항-이미지 일치 | 1.0 | 재생성 |
| `IMG_ANSWER_VERIFY` | 정답 이미지 검증 가능 | 1.0 | 재생성 |
| `IMG_DISTRACTOR_VALID` | 오답 이미지 기반 타당성 | 0.8 | 경고 |
| `IMG_EXPLANATION_MATCH` | 해설-이미지 일치 | 0.7 | 경고 |
| `IMG_NO_HALLUCINATION` | 이미지 외 정보 사용 없음 | 1.0 | 재생성 |

### 5.3 계산 검증 (AG-CALC) - 수학, 과학 ⚠️ Phase 2

| 코드 | 검증 항목 | 가중치 | 실패 시 처리 |
|------|----------|--------|-------------|
| `CALC_VERIFY` | 계산 정확성 | 1.0 | 재생성 |
| `UNIT_CHECK` | 단위 일관성 | 0.9 | 재생성 |
| `FORMULA_VALID` | 수식 유효성 | 0.9 | 재생성 |
| `STEP_LOGIC` | 풀이 단계 논리 | 0.8 | 경고 |

> ⚠️ 보안 샌드박스 환경 구축 필요 (Docker 또는 RestrictedPython)

### 5.4 사실 검증 (AG-FACT) - 역사, 사회 ⚠️ Phase 2

| 코드 | 검증 항목 | 가중치 | 실패 시 처리 |
|------|----------|--------|-------------|
| `FACT_VERIFY` | 사실 정확성 | 1.0 | **HOLD** (전문가 검토) |
| `DATE_VERIFY` | 연도 정확성 | 1.0 | **HOLD** (전문가 검토) |
| `SOURCE_VERIFY` | 출처 검증 | 0.9 | HOLD |
| `STAT_CURRENT` | 통계 최신성 | 0.7 | 경고 |

> ⚠️ 사실 검증은 외부 데이터 소스 의존도가 높아 자동 폐기보다 전문가 검토(HOLD) 권장

### 5.5 안전 검증 (AG-SAFE) - 국어, 영어, 역사, 사회 ⚠️ Phase 2

| 코드 | 검증 항목 | 가중치 | 실패 시 처리 |
|------|----------|--------|-------------|
| `BIAS_FREE` | 편향 없음 | 1.0 | HOLD (전문가 검토) |
| `SAFE_CONTENT` | 안전한 콘텐츠 | 1.0 | **즉시 폐기** |
| `SENSITIVE_TOPIC` | 민감 주제 | 0.9 | HOLD |
| `AGE_APPROPRIATE` | 연령 적합성 | 0.9 | 재생성 |

> ✅ LLM 프롬프트 기반으로 구현 가능 (Gemini Flash 활용)

---

## 6. 과목별 검증 파이프라인

### 6.1 국어/영어

```
                    ┌──────────┐
DraftItem ──▶ AG-VAL ──▶ AG-IMG ──▶ AG-SAFE ──▶ ValidationReport
                           │
                           ▼
                  [Gemini Vision]
                  이미지 정합성 검증
```

- 편향 및 유해 콘텐츠 검사 중심
- 지문 적절성 검토
- **이미지 포함 시 AG-IMG 적용**

### 6.2 수학

```
                    ┌──────────┐
DraftItem ──▶ AG-VAL ──▶ AG-IMG ──▶ AG-CALC ──▶ ValidationReport
                           │            │
                           ▼            ▼
                  [Gemini Vision]  [Code Execution]
                  이미지 정합성     Python + SymPy
```

- 계산 정확성 필수
- 정답 유일성 필수
- **이미지 포함 시 AG-IMG 적용**

### 6.3 과학

```
                    ┌──────────┐
DraftItem ──▶ AG-VAL ──▶ AG-IMG ──▶ AG-CALC ──▶ ValidationReport
                           │            │
                           ▼            ▼
                  [Gemini Vision]  [Code Execution]
                  이미지 정합성     Python + SymPy
```

- 계산 및 단위 검증
- 과학적 사실 정확성
- **이미지 포함 시 AG-IMG 적용**

### 6.4 역사/사회

```
                    ┌──────────┐
DraftItem ──▶ AG-VAL ──▶ AG-IMG ──▶ AG-FACT ──▶ AG-SAFE ──▶ ValidationReport
                           │            │
                           ▼            ▼
                  [Gemini Vision]  [외부 API 조회]
                  이미지 정합성     - 국사편찬위원회
                                  - 통계청 KOSIS
                                  - Wikipedia
```

- 사실 검증 필수
- 편향 검사 필수
- 외부 출처 확인
- **이미지 포함 시 AG-IMG 적용**

---

## 7. AG-IMG: 이미지 정합성 검증 ⭐

### 7.1 검증 프로세스

```python
class ImageConsistencyValidator:
    """이미지-문항 정합성 검증기 (Gemini Vision 기반)"""

    def validate(self, draft_item: DraftItem, image_path: Path) -> ValidationReport:
        """
        이미지와 문항의 정합성 검증

        검증 항목:
        1. 문항이 이미지 내용을 정확히 반영하는가?
        2. 정답이 이미지에서 도출 가능한가?
        3. 오답이 이미지 기반으로 합리적인가?
        4. 해설이 이미지 내용과 일치하는가?
        5. 이미지에 없는 정보를 사용하지 않았는가? (환각 방지)
        """
```

### 7.2 검증 프롬프트

```
당신은 교육 문항 검수 전문가입니다.

아래 문항이 이 이미지를 기반으로 올바르게 출제되었는지 검증하세요.

**문항 정보:**
- 질문: {stem}
- 선지: {choices}
- 정답: {correct_answer}
- 해설: {explanation}

**검증 기준:**
1. 문항의 질문이 이미지에서 확인 가능한 정보를 묻고 있는가?
2. 정답이 이미지에서 검증 가능한가?
3. 오답들이 합리적인 오류인가? (이미지와 완전히 무관하지 않은가?)
4. 해설이 이미지 내용과 일치하는가?
5. 정답이 유일한가? (복수 정답 가능성은 없는가?)

**응답 형식:**
{
    "is_valid": true/false,
    "failure_codes": ["IMG_QUESTION_MATCH", "IMG_ANSWER_VERIFY", ...],
    "details": ["상세 설명"],
    "recommendations": ["개선 권고"]
}
```

### 7.3 Failure Codes

| 코드 | 의미 | 심각도 | 구현 코드 |
|------|------|--------|----------|
| `IMG_QUESTION_MATCH` | 문항이 이미지와 무관함 | CRITICAL | `NO_VISUAL_EVIDENCE` |
| `IMG_ANSWER_VERIFY` | 정답을 이미지에서 확인 불가 | CRITICAL | `NO_VISUAL_EVIDENCE` |
| `IMG_DISTRACTOR_VALID` | 오답이 이미지와 무관함 | WARNING | `OPTION_OVERLAP` |
| `IMG_EXPLANATION_MATCH` | 해설이 이미지와 불일치 | WARNING | - |
| `IMG_NO_HALLUCINATION` | 이미지에 없는 정보 사용 | CRITICAL | `OUT_OF_SCOPE` |
| `IMG_AMBIGUOUS_READ` | 이미지 해석이 모호함 | WARNING | `AMBIGUOUS_READ` |
| `IMG_MULTI_CORRECT` | 이미지 기준 복수 정답 가능 | CRITICAL | `MULTI_CORRECT` |

> 📝 **현재 구현 코드**: `ConsistencyValidator`에서 사용하는 FailureCode enum
> - `AMBIGUOUS_READ`, `NO_VISUAL_EVIDENCE`, `MULTI_CORRECT`, `OPTION_OVERLAP`, `OUT_OF_SCOPE`

---

## 8. AG-CALC: Code Execution

### 8.1 샌드박스 환경

```python
class SandboxExecutor:
    def execute(self, code: str, timeout: int = 10) -> ExecutionResult:
        """격리된 환경에서 Python 코드 실행"""

    ALLOWED_IMPORTS = [
        "sympy", "numpy", "math", "fractions", "decimal"
    ]
```

### 8.2 수학 검증 예시

```python
def verify_math_answer(draft_item: DraftItem) -> CheckResult:
    code = f"""
import sympy as sp
x = sp.Symbol('x')
f = {parsed_expression}
result = sp.solve(f, x)
print(result)
"""
    result = sandbox.execute(code)
    return compare_with_answer(result, draft_item.correct_answer)
```

### 8.3 과학 검증 예시

```python
def verify_physics_calculation(draft_item: DraftItem) -> CheckResult:
    code = f"""
import sympy as sp
# 물리 공식 검증
v, u, a, t = sp.symbols('v u a t')
kinematic_eq = sp.Eq(v, u + a*t)
result = sp.solve(kinematic_eq.subs([(u, {initial}), (a, {accel}), (t, {time})]), v)
print(result)
"""
    result = sandbox.execute(code)
    return compare_with_answer(result, draft_item.correct_answer)
```

---

## 9. AG-FACT: 외부 데이터 연동 ⚠️ Phase 2

### 9.1 Wikipedia API (역사/사회 공통) - 1차

```python
def verify_fact_with_wikipedia(claim: str, language: str = "ko") -> FactCheckResult:
    """Wikipedia 기반 사실 검증"""
    import wikipedia
    wikipedia.set_lang(language)

    try:
        # 관련 페이지 검색
        search_results = wikipedia.search(claim, results=3)
        if not search_results:
            return FactCheckResult(verified=None, confidence=0.0)

        # 페이지 내용 확인
        page = wikipedia.page(search_results[0])

        # LLM으로 claim과 page.content 비교
        is_verified = llm_verify_claim(claim, page.content)

        return FactCheckResult(
            verified=is_verified,
            source=page.url,
            confidence=0.7 if is_verified else 0.3
        )
    except wikipedia.exceptions.DisambiguationError:
        return FactCheckResult(verified=None, confidence=0.0, note="모호한 검색어")
```

> ✅ 무료, 한국어 지원, pip install wikipedia

### 9.2 통계청 KOSIS API (사회) - 2차

```python
def verify_statistics(stat_claim: str, year: int) -> FactCheckResult:
    """통계 데이터 검증 (API 키 필요)"""
    response = kosis_api.query(
        indicator=stat_claim,
        year=year
    )
    return FactCheckResult(
        verified=abs(response.value - claimed_value) < threshold,
        source=f"KOSIS {response.indicator_name}",
        actual_value=response.value
    )
```

> ⚠️ KOSIS API 키 필요 (https://kosis.kr/openapi/)

### 9.3 LLM 기반 사실 확인 (보조)

```python
def llm_verify_claim(claim: str, reference_text: str) -> bool:
    """LLM을 활용한 사실 검증 (보조 수단)"""
    prompt = f"""
다음 주장이 참조 텍스트와 일치하는지 판단하세요.

**주장**: {claim}

**참조 텍스트**: {reference_text[:2000]}

**응답**: true 또는 false (JSON)
"""
    response = gemini_client.generate(prompt)
    return parse_boolean(response)
```

> ⚠️ LLM 환각 위험 - 외부 소스와 함께 사용 권장

---

## 10. 교차 검증 엔진

### 10.1 검증 레벨

| 레벨 | 모델 수 | 사용 모델 | 합의 기준 | 적용 상황 |
|------|--------|----------|----------|----------|
| Level 1 | 1 | Gemini Flash | 단일 검증 | 수학, 과학 |
| Level 2 | 2 | + GPT-4o | 2/2 합의 | 역사, 사회 |
| Level 3 | 3 | + Gemini Pro | 2/3 합의 | 민감 주제 |
| Level 4 | 3+ | + 전문가 | 전문가 최종 결정 | 공식 시험 |

### 10.2 불일치 처리

```
모델 A: PASS
모델 B: FAIL
모델 C: PASS
→ 2/3 합의 → PASS (단, 이슈 기록)
```

### 10.3 레벨 자동 결정

```python
def determine_validation_level(draft_item: DraftItem) -> int:
    """과목 및 주제에 따른 검증 레벨 결정"""
    subject = draft_item.subject

    if subject in ["history", "social"]:
        if contains_sensitive_topic(draft_item):
            return 3  # Level 3: 민감 주제
        return 2  # Level 2: 역사/사회 기본

    if subject in ["korean", "english"]:
        if contains_potentially_biased(draft_item):
            return 2
        return 1

    # 수학, 과학
    return 1  # Level 1: Code Execution으로 충분
```

---

## 11. 실패 처리

| 검증 실패 | 처리 방법 | 최대 재시도 | 구현 |
|----------|----------|:----------:|:----:|
| ANS_UNIQUE | P3 재생성 | 3회 | ✅ |
| ANS_CORRECT | P3 재생성 | 3회 | ⚠️ |
| **IMG_QUESTION_MATCH** | P3 재생성 | 3회 | ✅ |
| **IMG_ANSWER_VERIFY** | P3 재생성 | 3회 | ✅ |
| **IMG_NO_HALLUCINATION** | P3 재생성 | 3회 | ✅ |
| **IMG_MULTI_CORRECT** | P3 재생성 | 3회 | ✅ |
| CALC_VERIFY | P3 재생성 | 3회 | ❌ |
| FACT_VERIFY | **HOLD** (전문가 검토) | - | ❌ |
| BIAS_FREE | HOLD (전문가 검토) | - | ❌ |
| SAFE_CONTENT | **즉시 폐기** | - | ❌ |
| OPT_DISTINCT | P3 재생성 | 3회 | ✅ |
| SOURCE_VERIFY | HOLD (전문가 검토) | - | ❌ |

> ⚠️ FACT_VERIFY: 외부 데이터 소스 신뢰도 한계로 자동 폐기 대신 전문가 검토 권장

---

## 12. 오류 코드

| 코드 | 의미 | 처리 |
|------|------|------|
| E004-001 | 계산 검증 실패 | 재생성 |
| E004-002 | 정답 불일치 | 재생성 |
| E004-003 | 단위 오류 | 재생성 |
| E004-004 | 사실 검증 실패 | HOLD |
| E004-005 | 편향 감지 | HOLD |
| E004-006 | 유해 콘텐츠 감지 | 즉시 폐기 |
| E004-007 | 외부 API 오류 | 재시도 (3회) |
| E004-008 | 교차 검증 불일치 | HOLD |
| **E004-009** | **이미지 정합성 실패** | 재생성 |
| **E004-010** | **이미지 환각 감지** | 재생성 |
| **E004-011** | **이미지 분석 오류** | 재시도 (3회) |

---

## 13. 구현 로드맵

### Phase 1 (현재) ✅

| 항목 | 상태 | 구현 |
|------|:----:|------|
| AG-VAL (규칙 기반) | ✅ | `QualityChecker` |
| AG-IMG (이미지 정합성) | ✅ | `ConsistencyValidator` |
| 기본 ValidationReport | ✅ | `schemas.py` |
| 파이프라인 통합 | ✅ | `pipeline.py` |

### Phase 2 (예정)

| 항목 | 우선순위 | 난이도 | 의존성 |
|------|:--------:|:------:|--------|
| AG-SAFE (안전 검증) | **1** | 하 | Gemini Flash |
| AG-VAL 보완 (LLM 기반) | **2** | 중 | Gemini Flash |
| FailureCode 통일 | **3** | 하 | schemas.py 수정 |
| 교차검증 로직 | **4** | 중 | OpenAI API 키 |
| AG-CALC (계산 검증) | **5** | 상 | 보안 샌드박스 |
| AG-FACT (Wikipedia) | **6** | 중 | wikipedia 패키지 |

### Phase 3 (향후)

| 항목 | 설명 |
|------|------|
| AG-FACT (KOSIS) | 통계청 API 연동 |
| Level 4 전문가 검토 | UI/워크플로우 필요 |
| 실시간 모니터링 | 대시보드 구축 |

---

## 개정 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0.0 | 2026-02-01 | 초기 작성 |
| v1.3.0 | 2026-02-02 | AG-IMG 추가, 섹션 번호 수정 |
| v1.4.0 | 2026-02-02 | 현실 기반 조정 - 구현 현황 반영, AG-FACT Wikipedia로 변경, FACT_VERIFY HOLD로 변경 |

---

**문서 끝**
