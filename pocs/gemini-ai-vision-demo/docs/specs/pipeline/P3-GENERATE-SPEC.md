# P3-GENERATE 단계 명세

**문서 ID**: P3-GENERATE-SPEC-001
**버전**: v1.4.0
**수정일**: 2026-02-02
**목적**: 문항 생성 단계 상세 명세

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| **단계** | P3-GENERATE |
| **에이전트** | AG-GEN (Item Generator) |
| **모델** | Gemini 3 Flash |
| **입력** | `EvidencePack` + 생성 설정 |
| **출력** | `DraftItem` (현재: `ItemQuestion`) |
| **목표 시간** | 5~15초 |

### 1.1 구현 현황

| 기능 | 상태 | 구현 | 비고 |
|------|:----:|------|------|
| 기본 문항 생성 | ✅ | `ItemGeneratorAgent` | Gemini Vision 기반 |
| 유형별 프롬프트 | ✅ | GRAPH, GEOMETRY, MEASUREMENT | 3개 유형 |
| 난이도 조정 | ✅ | `_get_difficulty_instruction` | EASY/MEDIUM/HARD |
| 변형 유형 지원 | ❌ | - | Phase 2 |
| 이미지 위치 보존 | ❌ | - | Phase 2 |
| 과목별 생성 | ❌ | - | Phase 2 |
| 오답 유형 태깅 | ❌ | - | Phase 2 |

---

## 2. 변형 유형 ⚠️ Phase 2

> 현재는 `new` (신규 생성)만 지원. 변형 기능은 Phase 2에서 구현 예정.

### 2.1 기본 변형 유형

| 유형 | 코드 | 설명 | 예시 | 구현 |
|------|------|------|------|:----:|
| **유사** | `similar` | 수치/조건만 변경 | 85점→78점 | ❌ |
| **난이도↑** | `diff_up` | 복잡도 증가 | 2변수→3변수 | ❌ |
| **난이도↓** | `diff_down` | 단순화 | 연립→일차 | ❌ |
| **신규** | `new` | 완전 새 문항 | 동일 개념, 새 상황 | ✅ |

> 📝 스키마에 `VariationType` enum 정의됨 (`schemas.py`)

### 2.2 과목별 변형 전략 ⚠️ Phase 2

| 과목 | similar | diff_up | diff_down |
|------|---------|---------|-----------|
| **국어** | 지문 유사, 문제 동형 | 다중 지문, 복합 추론 | 단일 지문, 직접 추론 |
| **영어** | 어휘/문법 동형 | 긴 지문, 추론 문제 | 짧은 지문, 직접 이해 |
| **수학** | 수치 변경 | 변수/조건 추가 | 단계 축소 |
| **과학** | 수치/조건 변경 | 복합 현상, 다변인 | 단일 현상, 단일 변인 |
| **역사** | 동시대 다른 사건 | 인과관계 연결 | 단일 사건 |
| **사회** | 유사 통계, 다른 지역 | 다층 분석 | 단일 지표 |

> ⚠️ 과목별 생성은 Phase 2에서 구현 예정. 현재는 문항 유형(ItemType) 기반으로 동작.

---

## 3. 이미지 위치 보존 ⚠️ Phase 2

> 시나리오 B (원본+이미지 변형)에서 필요. 현재 미구현.

### 3.1 위치 정보 전달

```
[P1] 원본 위치 추출 (image_positions)
      ↓
[P2] EvidencePack에 위치 정보 포함
      ↓
[P3] DraftItem.visual_specification에 위치 정보 포함
      ↓
[P5] 원본 위치에 새 이미지 배치
```

### 3.2 위치 코드

| 위치 코드 | 설명 | IML 위치 |
|----------|------|---------|
| `before_stem` | 문제 앞 (지문 이미지) | `<물음>` 앞 |
| `after_stem` | 문제 뒤 (참고 그래프) | `<물음>` 내 `<그림>` |
| `inline` | 문장 내 | `<단락>` 내 `<그림>` |
| `in_choice` | 선지 내 | `<답항>` 내 `<그림>` |

### 3.3 위치 보존 로직

```python
def generate_with_position_preservation(evidence: EvidencePack) -> DraftItem:
    """위치 정보를 보존하며 문항 생성"""

    # 원본 위치 정보 추출
    original_positions = evidence.image_positions

    # 문항 생성
    draft_item = generate_item(evidence)

    # 시각 사양에 위치 정보 포함
    for i, visual_element in enumerate(evidence.visual_elements):
        position = original_positions[i] if i < len(original_positions) else None

        draft_item.visual_specification.elements.append(
            VisualSpecElement(
                position=position,  # ⭐ 원본 위치 유지
                visual_type=visual_element.element_type,
                data=transform_visual_data(visual_element.extracted_data),
            )
        )

    return draft_item
```

---

## 4. 출력: DraftItem

> 📝 현재 구현: `ItemQuestion` (schemas.py)

```python
# 스펙 (목표)
@dataclass
class DraftItem:
    item_id: str                        # 생성된 문항 ID          ✅ 구현됨
    stem: str                           # 발문                    ✅ 구현됨
    choices: List[Choice]               # 선택지 (5개)            ✅ 구현됨
    correct_answer: str                 # 정답 (①~⑤)             ✅ 구현됨
    explanation: str                    # 해설                    ✅ 구현됨
    solution_steps: List[str]           # 풀이 단계 (수학/과학)    ❌ Phase 2
    visual_specification: VisualSpec    # ⭐ 이미지 생성 사양      ⚠️ 기본만
    difficulty_estimate: str            # 예상 난이도              ✅ difficulty
    curriculum_alignment: List[str]     # 성취기준                 ❌ Phase 3
    generation_config: dict             # 생성에 사용된 설정       ❌ Phase 2
    subject: str                        # 과목                    ❌ item_type만
```

### 4.0 현재 구현 (ItemQuestion)

```python
class ItemQuestion(BaseModel):
    item_id: str
    item_type: ItemType          # GRAPH | GEOMETRY | MEASUREMENT
    difficulty: DifficultyLevel  # EASY | MEDIUM | HARD
    stem: str
    choices: list[Choice]        # label, text만
    correct_answer: str
    explanation: str
    evidence: EvidencePack
    source_image: str
    visual_spec: Optional[VisualSpec]
    generated_image: Optional[GeneratedImage]
```

### 4.1 Choice

```python
# 스펙 (목표)
@dataclass
class Choice:
    label: str           # ①, ②, ③, ④, ⑤              ✅ 구현됨 (A, B, C, D)
    text: str            # 선택지 내용                  ✅ 구현됨
    is_correct: bool     # 정답 여부                    ❌ Phase 2
    distractor_type: str # 오답 유형                    ❌ Phase 2
    has_image: bool      # ⭐ 이미지 포함 여부          ❌ Phase 2
    image_spec: Optional[VisualSpecElement]           # ❌ Phase 2
```

### 4.1.1 현재 구현 (Choice)

```python
class Choice(BaseModel):
    label: str  # "A", "B", "C", "D"
    text: str   # 선택지 내용
```

### 4.2 오답 유형 (DistractorType) ⚠️ Phase 2

> 오답 품질 향상을 위한 분류. 현재 미구현.

| 유형 | 설명 | 예시 | 적용 과목 |
|------|------|------|----------|
| `SIGN_ERROR` | 부호 오류 | +4 대신 -4 | 수학, 과학 |
| `CALCULATION_ERROR` | 계산 실수 | 3×4=11 | 수학, 과학 |
| `CONCEPT_CONFUSION` | 개념 혼동 | 평균↔중앙값 | 전체 |
| `PARTIAL_SOLUTION` | 부분 풀이 | 중간 단계 값 | 수학, 과학 |
| `SIMILAR_VALUE` | 유사 수치 | 15 대신 14 또는 16 | 전체 |
| `UNIT_ERROR` | 단위 오류 | m 대신 cm | 수학, 과학 |
| `TIMELINE_ERROR` | 시대 혼동 | 조선→고려 | 역사 |
| `REGION_ERROR` | 지역 혼동 | 한국→일본 | 역사, 사회 |
| `CAUSATION_ERROR` | 인과관계 오류 | 원인↔결과 | 역사, 사회, 과학 |

> 💡 구현 시 프롬프트에서 오답 유형을 명시적으로 요청하여 태깅

### 4.3 VisualSpec (이미지 사양)

```python
@dataclass
class VisualSpec:
    required: bool                    # 이미지 필요 여부
    elements: List[VisualSpecElement] # 시각 요소 목록
    rendering_instructions: str       # 렌더링 지침

@dataclass
class VisualSpecElement:
    visual_type: str        # graph | geometry | diagram | map | chart | ...
    position: ImagePosition # ⭐ 배치 위치 (원본 위치 유지)
    description: str        # 시각 요소 설명
    data: dict              # 렌더링 데이터
```

---

## 5. 과목별 생성 규칙 ⚠️ Phase 2

> 현재는 **문항 유형(ItemType)** 기반으로 동작. 과목별 생성은 Phase 2에서 구현 예정.

### 5.0 현재 구현: 문항 유형별 생성

| ItemType | 설명 | 프롬프트 |
|----------|------|---------|
| `GRAPH` | 그래프 해석 | ✅ 구현됨 |
| `GEOMETRY` | 도형/공간 | ✅ 구현됨 |
| `MEASUREMENT` | 측정값 판독 | ✅ 구현됨 |

### 5.1 국어 ⚠️ Phase 2

- 지문의 논리 구조 유지
- 어휘 난이도 조정
- 추론 단계 수 조정

### 5.2 영어 ⚠️ Phase 2

- 어휘/문법 구조 유지
- 지문 길이 조정
- 문맥 추론 난이도 조정

### 5.3 수학 ⚠️ Phase 2

- 정답이 유일하게 결정되어야 함
- 계산 결과가 깔끔한 정수 또는 분수여야 함
- 선택지 간 명확한 구분
- **풀이 단계 포함** (solution_steps)
- **수식 LaTeX 형식**

> 현재 GRAPH, GEOMETRY 유형으로 부분 지원

### 5.4 과학 ⚠️ Phase 2

- 과학적 사실 기반
- 단위 정확성
- 실험/관찰 결과 일관성
- **실험 변인 명확화**

> 현재 MEASUREMENT 유형으로 부분 지원

### 5.5 역사 ⚠️ Phase 2

- **사실 검증 필수** (AG-FACT 연동)
- 연도, 인물, 사건 정확성
- 편향 없는 서술
- **시대 맥락 유지**

### 5.6 사회 ⚠️ Phase 2

- **통계 데이터 출처 명시**
- 지역/국가 정확성
- 편향 없는 서술
- **최신 데이터 반영**

---

## 6. 생성기 구현

### 6.0 현재 구현: 통합 방식

> 현재는 단일 프롬프트로 모든 요소(발문, 선지, 해설)를 한 번에 생성.

```python
# 현재 구현 (ItemGeneratorAgent)
class ItemGeneratorAgent:
    PROMPTS = {
        ItemType.GRAPH: "...",      # 그래프 전용 프롬프트
        ItemType.GEOMETRY: "...",   # 도형 전용 프롬프트
        ItemType.MEASUREMENT: "..." # 측정 전용 프롬프트
    }

    def generate_item(self, image_path, item_type, difficulty) -> ItemQuestion:
        prompt = self.PROMPTS[item_type]
        prompt += self._get_difficulty_instruction(difficulty)

        result = self.vision_client.analyze_image_with_agentic_vision(
            image_path=image_path,
            prompt=prompt
        )

        return self._parse_item_from_response(result)
```

### 6.1 StemGenerator ⚠️ Phase 3

> 컴포넌트 분리는 복잡도 대비 효과가 낮아 Phase 3로 이동

```python
class StemGenerator:
    def generate(self, evidence: EvidencePack, config: dict) -> str:
        """발문 생성 (독립 컴포넌트)"""
```

### 6.2 ChoiceGenerator ⚠️ Phase 3

```python
class ChoiceGenerator:
    def generate(self, stem: str, answer: str, count: int = 5) -> List[Choice]:
        """선택지 생성 (정답 + 오답 4개)"""
```

### 6.3 ExplanationGenerator ⚠️ Phase 3

```python
class ExplanationGenerator:
    def generate(self, item: DraftItem, subject: str) -> str:
        """해설 생성 (과목별 특화)"""
```

### 6.4 VisualSpecGenerator

```python
# 현재 구현 (pipeline.py)
def _create_visual_spec(self, item: ItemQuestion, item_type: ItemType) -> VisualSpec:
    """문항 유형에 맞는 시각 사양 생성"""
    visual_type_map = {
        ItemType.GRAPH: "bar_chart",
        ItemType.GEOMETRY: "geometry",
        ItemType.MEASUREMENT: "diagram",
    }
    # ...
```

---

## 7. 프롬프트 템플릿

### 7.0 현재 구현된 프롬프트

#### GRAPH (그래프)

```
이 이미지는 그래프입니다.

**분석 지시:**
1. 그래프의 유형(막대, 선, 원 등)을 파악하세요.
2. 필요하다면 특정 구간을 확대하여 수치를 정확히 확인하세요.
3. 축의 레이블, 범례, 데이터 포인트를 정확히 읽으세요.

**출력 요구사항:**
그래프에서 직접 확인 가능한 정보만을 사용하여 객관식 문항 1개를 생성하세요.

반드시 다음 JSON 형식으로만 응답하세요:
{
    "stem": "문항 질문",
    "choices": [{"label": "A", "text": "선지1"}, ...],
    "correct_answer": "정답 레이블",
    "explanation": "해설 (시각 근거 포함)",
    "evidence_facts": ["근거1", "근거2"]
}
```

#### 난이도 지시문 (현재 구현)

```python
EASY: "이미지에서 직접 읽을 수 있는 단순한 정보를 묻는 문항"
MEDIUM: "이미지 정보를 바탕으로 한 단계 추론이 필요한 문항"
HARD: "이미지의 여러 정보를 종합하여 분석해야 하는 문항"
```

### 7.1 목표 프롬프트 (Phase 2) ⚠️

```
당신은 교육 평가 문항 출제 전문가입니다.

다음 분석 결과를 바탕으로 {variation_type} 문항을 생성하세요:

[과목]
{subject}

[난이도]
{difficulty}

[원본 분석]
{evidence_pack}

[이미지 위치 정보]
{image_positions}

[요구사항]
- 원본 이미지의 위치를 유지하세요
- 선택지 5개 (정답 1개 + 오답 4개)
- 오답은 타당한 오답 유형으로 구성
- 해설 포함
- {subject_specific_requirements}

[응답 형식]
{draft_item_schema}
```

### 7.2 과목별 요구사항 ⚠️ Phase 2

**수학**:
```
- 정답이 유일해야 합니다
- 계산 결과는 깔끔한 수(정수 또는 간단한 분수)여야 합니다
- 풀이 단계를 solution_steps에 포함하세요
- 수식은 LaTeX 형식으로 작성하세요
```

**역사/사회**:
```
- 사실 정확성을 우선하세요
- 편향되지 않은 서술을 사용하세요
- 연도, 인물, 사건명은 정확해야 합니다
- 출처가 필요한 통계는 명시하세요
```

---

## 8. 품질 기준

| 지표 | 목표값 | 검증 방법 | 구현 |
|------|--------|----------|:----:|
| 정답 유일성 | 100% | P4 AG-VAL | ⚠️ |
| 선택지 구분성 | > 90% | P4 AG-VAL | ✅ |
| 난이도 적합성 | > 80% | P4 AG-VAL | ❌ |
| 교육과정 부합 | > 95% | P4 AG-VAL | ❌ |
| 이미지 위치 보존율 | 100% | P5 확인 | ❌ |

> 품질 검증은 P4-VALIDATE에서 수행

---

## 9. 오류 코드

| 코드 | 의미 | 처리 | 구현 |
|------|------|------|:----:|
| E003-001 | 문항 생성 실패 | 재시도 (3회) | ✅ |
| E003-002 | 정답 불명확 | 재생성 | ⚠️ |
| E003-003 | 선택지 중복 | 재생성 | ✅ |
| E003-004 | 교육과정 불부합 | 경고 기록 | ❌ |
| E003-005 | 이미지 사양 생성 실패 | 텍스트 전용으로 진행 | ✅ |
| E003-006 | 위치 정보 손실 | 기본 위치 적용 | ❌ |

---

## 10. 구현 로드맵

### Phase 1 (현재) ✅

| 항목 | 상태 | 구현 |
|------|:----:|------|
| 기본 문항 생성 | ✅ | `ItemGeneratorAgent` |
| 유형별 프롬프트 (3종) | ✅ | GRAPH, GEOMETRY, MEASUREMENT |
| 난이도 조정 | ✅ | `_get_difficulty_instruction` |
| JSON 응답 파싱 | ✅ | `_parse_item_from_response` |
| 시각 사양 생성 | ✅ | `_create_visual_spec` |

### Phase 2 (예정)

| 항목 | 우선순위 | 난이도 | 의존성 |
|------|:--------:|:------:|--------|
| 변형 유형 (similar) | **1** | 중 | P1 InputPack |
| Choice 확장 (is_correct) | **2** | 하 | schemas.py |
| solution_steps 추가 | **3** | 하 | 프롬프트 수정 |
| DistractorType 태깅 | **4** | 중 | 프롬프트 수정 |
| 과목별 프롬프트 | **5** | 중 | 프롬프트 템플릿 |
| 이미지 위치 보존 | **6** | 상 | P1, P5 연동 |

### Phase 3 (향후)

| 항목 | 설명 |
|------|------|
| curriculum_alignment | 교육과정 DB 연동 필요 |
| Generator 컴포넌트 분리 | 복잡도 대비 효과 낮음 |
| 변형 유형 (diff_up, diff_down) | similar 구현 후 |

---

## 개정 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0.0 | 2026-02-01 | 초기 작성 |
| v1.2.0 | 2026-02-02 | 이미지 위치 보존 섹션 추가 |
| v1.4.0 | 2026-02-02 | 현실 기반 조정 - 구현 현황 반영, Phase 구분 |

---

**문서 끝**
