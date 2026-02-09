# P2-ANALYZE 단계 명세

**문서 ID**: P2-ANALYZE-SPEC-001
**버전**: v1.4.0
**수정일**: 2026-02-02
**목적**: Vision 분석 단계 상세 명세

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| **단계** | P2-ANALYZE |
| **에이전트** | AG-VIS (Vision Explorer) |
| **모델** | Gemini 3 Flash |
| **입력** | `InputPack` (현재: 이미지 경로) |
| **출력** | `EvidencePack` |
| **목표 시간** | 3~8초 |

### 1.1 구현 현황

| 기능 | 상태 | 구현 | 비고 |
|------|:----:|------|------|
| 기본 Vision 분석 | ✅ | `GeminiVisionClient` | Gemini 3 Flash |
| Agentic Vision | ✅ | `enable_code_execution` | 코드 실행 지원 |
| 단계별 로깅 | ✅ | `PhaseLog` (THINK/ACT/OBSERVE) | |
| EvidencePack 생성 | ✅ | `extract_evidence` | 단순 스키마 |
| 분석 유형 분기 | ❌ | - | Phase 2 |
| 과목별 분석 | ❌ | - | Phase 2 |
| 전문 Analyzer | ❌ | - | Phase 3 |
| 이미지 위치 활용 | ❌ | - | Phase 2 |

---

## 2. AG-VIS 에이전트

### 2.0 현재 구현

```python
# GeminiVisionClient (vision_client.py)
class GeminiVisionClient:
    def analyze_image_with_agentic_vision(
        self,
        image_path: str | Path,
        prompt: str,
        enable_code_execution: bool = True  # ✅ Agentic Vision
    ) -> dict:
        """이미지 분석 - 단계별 로깅 포함"""

    def extract_evidence(self, analysis_result: dict) -> EvidencePack:
        """분석 결과에서 EvidencePack 추출"""
```

### 2.1 역할

- 문항 이미지 시각적 분석 ✅
- 그래프, 도형, 표 등 시각 요소 추출 ✅ (통합 프롬프트)
- 수식 및 텍스트 OCR ✅ (Gemini 내장)
- 문항 구조 분석 ⚠️ (부분)
- **이미지 위치 정보 활용** ❌ Phase 2

### 2.2 분석 유형 (과목별) ⚠️ Phase 2

> 현재는 통합 프롬프트로 처리. 유형별 분기는 Phase 2에서 구현 예정.

| 유형 | 분석 대상 | 추출 데이터 | 적용 과목 | 구현 |
|------|----------|------------|----------|:----:|
| `graph` | 함수 그래프 | 함수식, 점근선, 교점 | 수학 | ⚠️ |
| `geometry` | 도형 | 꼭짓점, 변의 길이, 각도 | 수학 | ⚠️ |
| `diagram` | 다이어그램 | 관계, 흐름, 구조 | 전체 | ⚠️ |
| `table` | 표 | 행/열 데이터, 헤더 | 전체 | ⚠️ |
| `chart` | 통계 그래프 | 막대/선/원 그래프 데이터 | 수학, 사회 | ⚠️ |
| `map` | 지도 | 지역, 경로, 위치 | 역사, 사회 | ❌ |
| `timeline` | 연표 | 시대, 사건, 연도 | 역사 | ❌ |
| `experiment` | 실험 도표 | 실험 데이터, 결과 | 과학 | ⚠️ |
| `passage` | 지문/지문 이미지 | 텍스트, 인용 | 국어, 영어 | ❌ |
| `image` | 일반 이미지 | 설명, 레이블 | 전체 | ✅ |

> ⚠️ = 통합 프롬프트로 부분 지원, ❌ = 미구현

### 2.3 과목별 분석 초점 ⚠️ Phase 2

> 현재는 ItemType (GRAPH, GEOMETRY, MEASUREMENT) 기반으로 동작.

| 과목 | 주요 분석 유형 | 특수 처리 | 구현 |
|------|--------------|----------|:----:|
| **국어** | passage, diagram | 지문 구조, 논리 흐름 | ❌ |
| **영어** | passage, image | 지문, 삽화 맥락 | ❌ |
| **수학** | graph, geometry, table | 수식 LaTeX 변환 | ⚠️ |
| **과학** | experiment, diagram, graph | 실험 데이터 정확성 | ⚠️ |
| **역사** | map, timeline, image | 시대/사건 교차 검증 | ❌ |
| **사회** | map, chart, table | 통계 데이터 검증 | ❌ |

---

## 3. 입력

### 3.0 현재 구현

```python
# 현재는 이미지 경로만 직접 전달
result = vision_client.analyze_image_with_agentic_vision(
    image_path=image_path,  # 단순 경로
    prompt=prompt,
    enable_code_execution=True
)
```

### 3.1 목표: InputPack 활용 ⚠️ Phase 2

```python
# P1에서 전달받은 InputPack
input_pack: InputPack
    request_id: str
    qti_item: Optional[QTIItem]  # 원본 문항 (있는 경우)
    images: List[ImageInfo]       # 검증된 이미지
    image_positions: List[ImagePosition]  # ⭐ 이미지 위치 정보
    subject: str                  # 과목
    ...
```

### 3.2 이미지 위치 정보 활용 ⚠️ Phase 2

```python
def analyze_with_positions(input_pack: InputPack) -> EvidencePack:
    """위치 정보를 포함한 분석"""
    for image, position in zip(input_pack.images, input_pack.image_positions):
        # 위치에 따른 분석 전략 결정
        if position.location == "in_choice":
            # 선지 내 이미지 - 선지별 분석
            analyze_choice_image(image, position.choice_index)
        elif position.location == "before_stem":
            # 지문 이미지 - 전체 맥락 분석
            analyze_passage_image(image)
        else:
            # 참고 이미지 - 데이터 추출 중심
            analyze_reference_image(image)
```

---

## 4. 출력: EvidencePack

### 4.0 현재 구현

```python
# schemas.py - 현재 EvidencePack
class EvidencePack(BaseModel):
    regions: list[Region] = []           # 분석된 영역들
    extracted_facts: list[str] = []      # 추출된 사실들 ✅
    analysis_summary: str = ""           # 분석 요약 ✅
```

```python
# vision_client.py - extract_evidence
def extract_evidence(self, analysis_result: dict) -> EvidencePack:
    evidence = EvidencePack(
        analysis_summary=analysis_result.get("text", "")[:500]
    )
    # 텍스트에서 사실 추출 (-, *, • 로 시작하는 라인)
    for line in lines:
        if line.startswith(("-", "*", "•")):
            evidence.extracted_facts.append(line)
    return evidence
```

### 4.1 목표 스키마 ⚠️ Phase 2

```python
@dataclass
class EvidencePack:
    source_item_id: str                    # 원본 문항 ID         ❌
    extracted_text: str                    # OCR 텍스트           ❌
    visual_elements: List[VisualElement]   # 시각 요소 목록       ❌
    data_values: Dict[str, Any]            # 추출된 데이터 값     ❌
    mathematical_expressions: List[str]    # 수식 목록            ❌
    key_concepts: List[str]                # 핵심 개념            ❌
    structure_analysis: StructureAnalysis  # 문항 구조 분석       ❌
    image_positions: List[ImagePosition]   # ⭐ 위치 정보 전달    ❌
    confidence: float                      # 분석 신뢰도          ❌

    # 현재 구현
    regions: list[Region]                  # ✅
    extracted_facts: list[str]             # ✅
    analysis_summary: str                  # ✅
```

### 4.2 VisualElement ⚠️ Phase 2

```python
@dataclass
class VisualElement:
    element_id: str
    element_type: str       # graph | geometry | diagram | table | map | ...
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    extracted_data: dict    # 유형별 추출 데이터
    position: ImagePosition # ⭐ 원본 위치 정보
    confidence: float
```

### 4.3 StructureAnalysis ⚠️ Phase 2

```python
@dataclass
class StructureAnalysis:
    item_type: str          # 문항 유형 (선택형, 단답형, 서술형)
    stem_analysis: dict     # 발문 분석
    choice_analysis: dict   # 선택지 분석
    answer_derivation: str  # 정답 도출 근거
    subject_specific: dict  # 과목별 특화 분석
```

---

## 5. 분석기 구현

### 5.0 현재 구현: 통합 방식

> 현재는 Gemini Vision의 통합 프롬프트로 모든 분석 수행.
> 전문 Analyzer 컴포넌트 분리는 복잡도 대비 효과가 낮아 Phase 3로 이동.

```python
# 현재 구현 (GeminiVisionClient)
def analyze_image_with_agentic_vision(self, image_path, prompt, enable_code_execution=True):
    """
    통합 분석 - Gemini Vision이 이미지 유형을 자동 판별
    - Code Execution으로 수치 계산 지원
    - 단계별 로깅 (THINK → ACT → OBSERVE)
    """
```

### 5.1 GraphAnalyzer ⚠️ Phase 3

```python
class GraphAnalyzer:
    def analyze(self, image: Image) -> GraphData:
        """함수 그래프 분석"""
        # - 함수 유형 식별 (일차, 이차, 삼각, 지수, 로그)
        # - 주요 점 추출 (교점, 극값, 점근선)
        # - 함수식 추론
```

### 5.2 GeometryAnalyzer ⚠️ Phase 3

```python
class GeometryAnalyzer:
    def analyze(self, image: Image) -> GeometryData:
        """도형 분석"""
```

### 5.3 MapAnalyzer ⚠️ Phase 3

```python
class MapAnalyzer:
    def analyze(self, image: Image) -> MapData:
        """지도 분석"""
```

### 5.4 TimelineAnalyzer ⚠️ Phase 3

```python
class TimelineAnalyzer:
    def analyze(self, image: Image) -> TimelineData:
        """연표 분석"""
```

### 5.5 ExperimentAnalyzer ⚠️ Phase 3

```python
class ExperimentAnalyzer:
    def analyze(self, image: Image) -> ExperimentData:
        """실험 도표 분석"""
```

### 5.6 TableAnalyzer ⚠️ Phase 3

```python
class TableAnalyzer:
    def analyze(self, image: Image) -> TableData:
        """표 분석"""
```

### 5.7 MathExpressionParser ⚠️ Phase 3

```python
class MathExpressionParser:
    def parse(self, text: str) -> List[MathExpression]:
        """수식 파싱 - LaTeX 변환, SymPy 표현식 생성"""
```

> 💡 Phase 3에서 필요시 구현. 현재는 Gemini Vision 통합 분석으로 충분.

---

## 6. 프롬프트 템플릿

### 6.0 현재 사용 프롬프트

> P3-GENERATE의 ItemGeneratorAgent에서 P2 분석과 P3 생성을 통합 수행

```python
# item_generator.py의 PROMPTS (분석+생성 통합)
PROMPTS = {
    ItemType.GRAPH: """이 이미지는 그래프입니다.

**분석 지시:**
1. 그래프의 유형(막대, 선, 원 등)을 파악하세요.
2. 필요하다면 특정 구간을 확대하여 수치를 정확히 확인하세요.
3. 축의 레이블, 범례, 데이터 포인트를 정확히 읽으세요.
..."""
}
```

### 6.1 목표: 분석 전용 프롬프트 ⚠️ Phase 2

```
당신은 교육 평가 문항 분석 전문가입니다.

다음 문항과 이미지를 분석하고 JSON 형식으로 응답하세요:

[분석 항목]
1. 문항 유형 식별 (객관식/주관식, 그래프/도형/표 등)
2. 시각 요소 추출 (좌표, 수치, 레이블)
3. 수식 및 기호 추출 (LaTeX 형식)
4. 핵심 개념 및 성취기준 식별
5. 정답 도출 과정 분석

[과목]
{subject}

[이미지 위치 정보]
{image_positions}

[응답 형식]
{evidence_pack_schema}
```

### 6.2 과목별 특화 프롬프트 ⚠️ Phase 2

**수학**:
```
[추가 분석]
- 함수식을 LaTeX로 정확히 표현하세요
- 그래프의 모든 특징점(극값, 교점, 점근선)을 추출하세요
- 도형의 정확한 수치와 관계를 파악하세요
```

**역사/사회**:
```
[추가 분석]
- 지도의 지역/경로를 정확히 식별하세요
- 연표의 사건-연도 매핑을 추출하세요
- 통계 데이터의 출처와 시점을 확인하세요
```

**과학**:
```
[추가 분석]
- 실험의 독립변인과 종속변인을 식별하세요
- 측정값과 단위를 정확히 추출하세요
- 데이터의 패턴이나 경향성을 분석하세요
```

---

## 7. 품질 기준

| 지표 | 목표값 | 측정 방법 | 구현 |
|------|--------|----------|:----:|
| 텍스트 추출 정확도 | > 95% | 수동 검증 | ⚠️ |
| 수식 인식 정확도 | > 90% | LaTeX 변환 | ⚠️ |
| 그래프 데이터 정확도 | > 85% | 수치 추출 | ⚠️ |
| 도형 인식 정확도 | > 90% | 형태 인식 | ⚠️ |
| 지도 지역 인식 정확도 | > 80% | 역사/사회 | ❌ |
| 연표 연도 추출 정확도 | > 95% | 역사 | ❌ |
| 실험 데이터 정확도 | > 90% | 과학 | ⚠️ |

> ⚠️ Gemini Vision 내장 기능으로 부분 지원

---

## 8. 오류 코드

| 코드 | 의미 | 처리 | 구현 |
|------|------|------|:----:|
| E002-001 | 이미지 분석 실패 | 재시도 (3회) | ✅ |
| E002-002 | OCR 실패 | 대체 OCR 시도 | ❌ |
| E002-003 | 수식 파싱 실패 | 텍스트로 대체 | ❌ |
| E002-004 | 데이터 추출 불완전 | 경고 기록, 계속 | ⚠️ |
| E002-005 | 과목 불일치 | 과목 재확인 요청 | ❌ |

---

## 9. 구현 로드맵

### Phase 1 (현재) ✅

| 항목 | 상태 | 구현 |
|------|:----:|------|
| Gemini Vision 클라이언트 | ✅ | `GeminiVisionClient` |
| Agentic Vision (Code Execution) | ✅ | `enable_code_execution` |
| 단계별 로깅 | ✅ | `PhaseLog` (THINK/ACT/OBSERVE) |
| EvidencePack 기본 | ✅ | `extract_evidence` |

### Phase 2 (예정)

| 항목 | 우선순위 | 난이도 | 의존성 |
|------|:--------:|:------:|--------|
| P1 InputPack 연동 | **1** | 중 | P1 구현 |
| 분석 유형 분기 | **2** | 중 | 프롬프트 분리 |
| EvidencePack 확장 | **3** | 중 | 스키마 수정 |
| 과목별 분석 프롬프트 | **4** | 중 | 프롬프트 템플릿 |
| 이미지 위치 활용 | **5** | 상 | P1 연동 |

### Phase 3 (향후)

| 항목 | 설명 |
|------|------|
| 전문 Analyzer 컴포넌트 | GraphAnalyzer, GeometryAnalyzer 등 |
| VisualElement 스키마 | 상세 시각 요소 추출 |
| StructureAnalysis | 문항 구조 분석 |

---

## 개정 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0.0 | 2026-02-01 | 초기 작성 |
| v1.2.0 | 2026-02-02 | 과목별 분석 유형 추가 |
| v1.4.0 | 2026-02-02 | 현실 기반 조정 - 구현 현황 반영, Phase 구분 |

---

**문서 끝**
