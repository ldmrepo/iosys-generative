# P5-OUTPUT 단계 명세

**문서 ID**: P5-OUTPUT-SPEC-001
**버전**: v1.2.0
**수정일**: 2026-02-02
**목적**: 최종 출력 단계 상세 명세

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| **단계** | P5-OUTPUT |
| **에이전트** | AG-IMG, AG-STD, AG-AUD |
| **입력** | 검증된 `DraftItem` |
| **출력** | `FinalItem` + 이미지 + 감사 로그 |
| **목표 시간** | 이미지 없음 < 3초, 이미지 포함 < 60초 |

---

## 2. 출력 에이전트

### 2.1 AG-IMG (Image Generator)

- **모델**: Nano Banana Pro (gemini-3-pro-image-preview)
- 문항 시각 자료 생성
- 그래프, 도형, 다이어그램, 지도, 차트
- **이미지 위치 보존** ⭐

### 2.2 AG-STD (Standardizer)

- 용어 표준화
- 단위 표기 통일
- 기호 정규화

### 2.3 AG-AUD (Audit Logger)

- 전체 처리 과정 기록
- 추적 가능성 보장
- 감사 로그 생성

---

## 3. 이미지 위치 보존 ⭐

### 3.1 위치 코드

| 위치 코드 | 설명 | IML 출력 위치 |
|----------|------|--------------|
| `before_stem` | 문제 앞 (지문 이미지) | `<물음>` 앞 |
| `after_stem` | 문제 뒤 (참고 그래프) | `<물음>` 내 `<그림>` |
| `inline` | 문장 내 | `<단락>` 내 `<그림>` |
| `in_choice` | 선지 내 | `<답항>` 내 `<그림>` |

### 3.2 위치 보존 로직

```python
def place_images_at_original_positions(
    draft_item: DraftItem,
    generated_images: List[GeneratedImage]
) -> FinalItem:
    """원본 위치에 새 이미지 배치"""

    final_item = FinalItem(base=draft_item)

    for image, spec_element in zip(generated_images, draft_item.visual_specification.elements):
        position = spec_element.position  # P1에서 추출한 원본 위치

        if position.location == "before_stem":
            final_item.before_stem_images.append(image)
        elif position.location == "after_stem":
            final_item.after_stem_images.append(image)
        elif position.location == "inline":
            final_item.inline_images.append({
                "paragraph_index": position.paragraph_index,
                "image": image
            })
        elif position.location == "in_choice":
            final_item.choices[position.choice_index].image = image

    return final_item
```

### 3.3 위치 정보 전달 흐름

```
[P1] 원본 위치 추출 → image_positions: List[ImagePosition]
      ↓
[P2] EvidencePack에 위치 정보 포함
      ↓
[P3] DraftItem.visual_specification에 위치 정보 포함
      ↓
[P5] 원본 위치에 새 이미지 배치 ⭐
```

---

## 4. 출력: FinalItem

```python
@dataclass
class FinalItem:
    # 기본 정보
    item_id: str
    source_item_id: str
    version: int

    # 문항 내용
    subject: str
    grade: str
    difficulty: str
    stem: str
    choices: List[Choice]
    correct_answer: str
    explanation: str

    # 메타데이터
    curriculum_standards: List[str]
    keywords: List[str]

    # 첨부 이미지 (위치별) ⭐
    before_stem_images: List[GeneratedImage]  # 문제 앞
    after_stem_images: List[GeneratedImage]   # 문제 뒤
    inline_images: List[dict]                  # 문장 내 (paragraph_index 포함)

    # 품질
    validation_score: float
    validation_summary: dict
    human_reviewed: bool

    # 추적
    created_at: datetime
    audit_log_id: str
```

### 4.1 GeneratedImage

```python
@dataclass
class GeneratedImage:
    image_id: str
    path: str
    format: str             # PNG
    resolution: str         # 1K, 2K, 4K
    aspect_ratio: str       # 1:1, 3:4, 4:3, 9:16, 16:9
    visual_spec: VisualSpec # 생성 사양
    position: ImagePosition # ⭐ 배치 위치
    generation_model: str   # gemini-3-pro-image-preview
    generated_at: datetime
```

---

## 5. AG-IMG: Nano Banana Pro

### 5.1 이미지 해상도 옵션 ⭐

| 옵션 | 해상도 | 파일 크기 (예상) | 용도 |
|------|--------|-----------------|------|
| **1K** | 1024×1024 | ~300KB | 기본값, 웹/모바일 |
| **2K** | 2048×2048 | ~1.2MB | 고해상도 |
| **4K** | 4096×4096 | ~4.8MB | 인쇄용 |

### 5.2 종횡비 옵션 ⭐

| 옵션 | 비율 | 용도 |
|------|------|------|
| **1:1** | 정사각형 | 기본값, 도형/차트 |
| **3:4** | 세로형 | 문서 삽입 |
| **4:3** | 가로형 | 그래프/표 |
| **9:16** | 세로 와이드 | 모바일 |
| **16:9** | 가로 와이드 | 프레젠테이션 |

### 5.3 이미지 생성

```python
def generate_item_image(
    visual_spec: VisualSpec,
    resolution: str = "1K",      # ⭐ 기본값 1K
    aspect_ratio: str = "1:1"
) -> GeneratedImage:
    if not visual_spec.required:
        return None

    prompt = build_image_prompt(visual_spec)

    response = client.models.generate_content(
        model="gemini-3-pro-image-preview",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=resolution
            )
        )
    )

    return extract_and_save_image(response)
```

### 5.4 프롬프트 템플릿

```
교육용 {visual_type}을(를) 생성하세요.

[설명]
{description}

[데이터]
{data}

[요구사항]
- 교과서/시험지에 적합한 깔끔한 스타일
- 흰색 배경
- 모든 레이블과 텍스트 선명하게
- 한글 및 수학 기호 정확하게 렌더링
- 해상도: {resolution}
- 비율: {aspect_ratio}
```

### 5.5 지원 시각 유형 (과목별)

| 유형 | 설명 | 적용 과목 |
|------|------|----------|
| `function_graph` | 함수 그래프 | 수학 |
| `geometry` | 도형 (삼각형, 사각형, 원 등) | 수학 |
| `coordinate` | 좌표평면 | 수학 |
| `bar_chart` | 막대 그래프 | 수학, 사회 |
| `line_chart` | 선 그래프 | 수학, 과학, 사회 |
| `pie_chart` | 원 그래프 | 수학, 사회 |
| `map` | 지도 | 역사, 사회 |
| `timeline` | 연표 | 역사 |
| `experiment_diagram` | 실험 도표 | 과학 |
| `flowchart` | 순서도 | 전체 |
| `diagram` | 다이어그램 | 전체 |

---

## 6. AG-STD: 표준화 규칙

### 6.1 용어 표준화

| 비표준 | 표준 |
|--------|------|
| 가로, 밑변 | 밑변 |
| 세로, 높이 | 높이 |
| 반지름, 반경 | 반지름 |

### 6.2 단위 표기

| 비표준 | 표준 |
|--------|------|
| cm², ㎠ | cm² |
| m/s, m/sec | m/s |
| kg, KG | kg |

### 6.3 수학 기호

| 비표준 | 표준 |
|--------|------|
| ×, x | × |
| ÷, / | ÷ |
| ≤, <= | ≤ |

---

## 7. AG-AUD: 감사 로그

### 7.1 로그 스키마

```python
@dataclass
class AuditLog:
    log_id: str
    item_id: str
    request_id: str

    # 타임라인
    started_at: datetime
    completed_at: datetime
    duration_ms: int

    # 단계별 기록
    stages: List[StageLog]

    # 결과
    final_status: str
    error_code: Optional[str]
```

### 7.2 StageLog

```python
@dataclass
class StageLog:
    stage: str            # P1, P2, P3, P4, P5
    started_at: datetime
    completed_at: datetime
    status: str           # SUCCESS | FAILED | SKIPPED
    input_hash: str       # 입력 데이터 해시
    output_hash: str      # 출력 데이터 해시
    model_used: str       # 사용된 모델
    token_usage: dict     # 토큰 사용량
    image_positions: List[ImagePosition]  # ⭐ 이미지 위치 정보
```

---

## 8. 출력 형식

### 8.1 IML 출력 (이미지 위치 보존)

```xml
<?xml version="1.0" encoding="utf-8"?>
<문항종류>
<단위문항>
<문항 id="{item_id}" qt="{question_type}" df="{difficulty}" cls4="{subject_code}">
  <문제>
    <!-- before_stem 이미지 -->
    <그림 w="{width}" h="{height}" ow="{original_width}" oh="{original_height}">
      {item_id}\DrawObjPic\before_stem_1.png
    </그림>
    <물음>
      <단락>
        <문자열>{stem_part1}</문자열>
      </단락>
      <!-- after_stem 이미지 -->
      <그림 w="{width}" h="{height}">
        {item_id}\DrawObjPic\after_stem_1.png
      </그림>
      <단락>
        <문자열>{stem_part2}</문자열>
      </단락>
    </물음>
    <답항><단락><문자열>{choice_1}</문자열></단락></답항>
    <답항><단락><문자열>{choice_2}</문자열></단락></답항>
    <!-- in_choice 이미지 -->
    <답항>
      <단락>
        <문자열>{choice_3_text}</문자열>
        <그림 w="{width}" h="{height}">
          {item_id}\DrawObjPic\choice_3.png
        </그림>
      </단락>
    </답항>
    <답항><단락><문자열>{choice_4}</문자열></단락></답항>
    <답항><단락><문자열>{choice_5}</문자열></단락></답항>
  </문제>
  <정답><단락><문자열>{correct_answer}</문자열></단락></정답>
  <해설><단락><문자열>{explanation}</문자열></단락></해설>
</문항>
</단위문항>
</문항종류>
```

### 8.2 QTI 출력

```xml
<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
                identifier="{item_id}"
                title="{title}">
  <itemBody>
    <p>{stem}</p>
    <img src="{image_url}" alt="{image_alt}"/>
    <choiceInteraction responseIdentifier="RESPONSE" maxChoices="1">
      <simpleChoice identifier="A">{choice_1}</simpleChoice>
      <simpleChoice identifier="B">{choice_2}</simpleChoice>
      <simpleChoice identifier="C">{choice_3}</simpleChoice>
      <simpleChoice identifier="D">{choice_4}</simpleChoice>
      <simpleChoice identifier="E">{choice_5}</simpleChoice>
    </choiceInteraction>
  </itemBody>
  <responseDeclaration identifier="RESPONSE" cardinality="single">
    <correctResponse>
      <value>{correct_answer}</value>
    </correctResponse>
  </responseDeclaration>
</assessmentItem>
```

---

## 9. 저장 구조

```
output/
├── items/
│   └── {item_id}.json       # FinalItem JSON
├── images/
│   └── {item_id}/
│       ├── before_stem_1.png
│       ├── after_stem_1.png
│       └── choice_3.png
├── iml/
│   └── {item_id}.xml        # IML XML
├── qti/
│   └── {item_id}.xml        # QTI XML
└── logs/
    └── {log_id}.json        # 감사 로그
```

---

## 10. 성능 목표

| 지표 | 이미지 없음 | 이미지 포함 (1K) | 이미지 포함 (2K) |
|------|-----------|-----------------|-----------------|
| 단일 문항 | < 3초 | < 30초 | < 60초 |
| 배치 처리 | 200문항/시간 | 60문항/시간 | 40문항/시간 |

---

## 11. 오류 코드

| 코드 | 의미 | 처리 |
|------|------|------|
| E005-001 | 이미지 생성 실패 | 텍스트 전용 출력 |
| E005-002 | 위치 보존 실패 | 기본 위치 (after_stem) |
| E005-003 | IML 변환 실패 | JSON만 저장 |
| E005-004 | QTI 변환 실패 | JSON만 저장 |
| E005-005 | 저장 실패 | 재시도 (3회) |
| E005-006 | 해상도 미지원 | 기본값 (1K) 적용 |
| E005-007 | 종횡비 미지원 | 기본값 (1:1) 적용 |

---

**문서 끝**
