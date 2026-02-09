# P1-INPUT 단계 명세

**문서 ID**: P1-INPUT-SPEC-001
**버전**: v1.2.0
**수정일**: 2026-02-02
**목적**: 입력 수집 및 전처리 단계 상세 명세

---

## 1. 개요

| 항목 | 내용 |
|------|------|
| **단계** | P1-INPUT |
| **역할** | QTI/IML 파싱, 이미지 검증, 위치 추출, 메타데이터 정규화 |
| **입력** | QTI/IML XML, 첨부 이미지, 메타데이터 |
| **출력** | `InputPack` |
| **목표 시간** | < 1초 |

---

## 2. 입력 시나리오

| 시나리오 | 입력 | 처리 |
|---------|------|------|
| **A** | 이미지만 | 이미지 검증 → InputPack (qti_item=null) |
| **B** | 원본 문항 + 이미지 | 문항 파싱 + 이미지 검증 + 위치 추출 |
| **C** | 원본 문항만 | 문항 파싱 (images=[]) |

---

## 3. 입력 사양

### 3.1 IML (한국 교육 문항 표준) ⭐ 우선 지원

```xml
<?xml version="1.0" encoding="utf-8"?>
<문항종류>
<단위문항>
<문항 id="ITEM001" qt="11" df="02" cls2="02" cls3="08" cls4="03">
  <문제>
    <물음>
      <단락>
        <문자열>다음 그래프를 보고 물음에 답하시오.</문자열>
      </단락>
      <그림 w="30.08" h="24.07" ow="1382" oh="1106">
        ITEM001\DrawObjPic\image.png
      </그림>
      <단락>
        <수식>{  f(x) = x^2 + 2x - 3  }</수식>
        <문자열>의 최솟값을 구하시오.</문자열>
      </단락>
    </물음>
    <답항><단락><문자열>-4</문자열></단락></답항>
    <답항><단락><문자열>-3</문자열></단락></답항>
    <답항><단락><문자열>-2</문자열></단락></답항>
    <답항><단락><문자열>-1</문자열></단락></답항>
    <답항><단락><문자열>0</문자열></단락></답항>
  </문제>
  <정답><단락><문자열>①</문자열></단락></정답>
  <해설><단락><문자열>해설 내용</문자열></단락></해설>
</문항>
</단위문항>
</문항종류>
```

**IML 속성 매핑**:

| 속성 | 의미 | 값 예시 |
|------|------|--------|
| qt | 문항유형 | 11(선택형), 31(단답형), 41(서술형) |
| df | 난이도 | 01(상), 02(중), 03(하) |
| cls2 | 학교급 | 01(초), 02(중), 03(고) |
| cls3 | 학년 | 08(2학년) |
| cls4 | 과목 | 01(국어), 02(영어), 03(수학), 04(사회), 05(과학), 06(역사) |

### 3.2 QTI 2.1/3.0 (향후 지원)

```xml
<assessmentItem xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"
                identifier="ITEM-001"
                title="이차함수 문항">
  <itemBody>
    <p>이차함수 f(x) = x² + 2x - 3의 최솟값을 구하시오.</p>
    <choiceInteraction responseIdentifier="RESPONSE" maxChoices="1">
      <simpleChoice identifier="A">-4</simpleChoice>
      ...
    </choiceInteraction>
  </itemBody>
</assessmentItem>
```

### 3.3 이미지

| 항목 | 요구사항 |
|------|---------|
| 포맷 | PNG, JPEG, WebP, GIF |
| 최대 크기 | 10MB |
| 최대 해상도 | 4096 x 4096 |
| 컬러 모드 | RGB, Grayscale |

### 3.4 메타데이터

```json
{
  "subject": "math",           // 과목
  "grade": "middle-2",         // 학년
  "difficulty": "medium",      // 난이도
  "variation_type": "similar", // 변형 유형
  "curriculum_standards": ["[10수학01-05]"]
}
```

---

## 4. 이미지 위치 추출 ⭐

### 4.1 위치 유형

| 위치 코드 | IML 위치 | 설명 |
|----------|---------|------|
| `before_stem` | `<물음>` 앞 | 지문 이미지 |
| `after_stem` | `<물음>` 내 `<그림>` | 참고 그래프/도형 |
| `inline` | `<단락>` 내 `<그림>` | 인라인 이미지 |
| `in_choice` | `<답항>` 내 `<그림>` | 선지 내 이미지 |

### 4.2 위치 정보 추출

```python
@dataclass
class ImagePosition:
    location: str         # before_stem, after_stem, inline, in_choice
    paragraph_index: int  # 단락 인덱스 (0-based)
    choice_index: int     # 선지 인덱스 (in_choice인 경우)
    width: float          # 원본 너비
    height: float         # 원본 높이
    original_path: str    # 원본 경로
```

### 4.3 위치 추출 로직

```python
def extract_image_positions(iml_element) -> List[ImagePosition]:
    positions = []

    # 물음 내 그림 요소 탐색
    for idx, element in enumerate(iml_element.findall('.//그림')):
        parent = element.getparent()

        if parent.tag == '답항':
            location = 'in_choice'
            choice_idx = get_choice_index(parent)
        elif parent.tag == '물음':
            location = 'after_stem'
            choice_idx = -1
        else:
            location = 'inline'
            choice_idx = -1

        positions.append(ImagePosition(
            location=location,
            paragraph_index=idx,
            choice_index=choice_idx,
            width=float(element.get('w', 0)),
            height=float(element.get('h', 0)),
            original_path=element.text.strip()
        ))

    return positions
```

---

## 5. 출력: InputPack

```python
@dataclass
class InputPack:
    # 기본 정보
    request_id: str              # 요청 고유 ID (REQ-XXXXXXXX)

    # 원본 문항
    qti_item: Optional[QTIItem]  # 파싱된 QTI/IML 문항

    # 이미지
    images: List[ImageInfo]      # 검증된 이미지 목록
    primary_image: Optional[str] # 주 이미지 경로
    image_positions: List[ImagePosition]  # ⭐ 이미지 위치 정보

    # 메타데이터
    subject: str                 # 과목 (korean, english, math, science, history, social)
    grade: str                   # 학년
    difficulty: str              # 난이도 (easy, medium, hard)
    variation_type: str          # 변형 유형 (similar, diff_up, diff_down, new)

    # 교육과정
    curriculum_meta: dict        # 교육과정 메타데이터

    # 검증
    is_valid: bool               # 유효성 여부
    validation_errors: List[str] # 검증 오류

    # 시간
    created_at: datetime         # 생성 시간
```

### 5.1 QTIItem

```python
@dataclass
class QTIItem:
    item_id: str
    source_path: Optional[Path]
    title: str
    stem: str                    # 문제 본문
    choices: List[Choice]        # 선지 목록
    correct_answer: str          # 정답
    explanation: str             # 해설
    images: List[str]            # 이미지 경로 목록
    math_expressions: List[str]  # 수식 목록
    question_type: str           # 문항 유형 코드
```

### 5.2 ImageInfo

```python
@dataclass
class ImageInfo:
    path: str
    format: str      # PNG, JPEG, etc.
    width: int
    height: int
    file_size: int   # bytes
    is_valid: bool
    validation_issues: List[str]
```

---

## 6. 처리 컴포넌트

### 6.1 QTIParser

```python
class QTIParser:
    ENCODINGS = ["euc-kr", "cp949", "utf-8", "utf-8-sig"]

    def parse(self, xml_path: Path) -> Optional[QTIItem]:
        """QTI/IML XML 파일 파싱"""

    def parse_string(self, xml_string: str) -> Optional[QTIItem]:
        """XML 문자열 파싱"""

    def validate_schema(self, xml_string: str) -> Tuple[bool, List[str]]:
        """스키마 유효성 검증"""

    def extract_image_positions(self, xml_element) -> List[ImagePosition]:
        """이미지 위치 추출"""
```

### 6.2 ImageProcessor

```python
class ImageProcessor:
    def validate(self, image_path: Path) -> ImageInfo:
        """이미지 검증 및 정보 추출"""

    def normalize(self, image_path: Path) -> bytes:
        """이미지 정규화 (크기 조정, 포맷 변환)"""
```

### 6.3 MetadataNormalizer

```python
class MetadataNormalizer:
    SUBJECT_CODES = {
        "01": "korean", "02": "english", "03": "math",
        "04": "social", "05": "science", "06": "history",
        "국어": "korean", "영어": "english", "수학": "math",
        "사회": "social", "과학": "science", "역사": "history"
    }

    DIFFICULTY_CODES = {
        "01": "hard", "02": "medium", "03": "easy",
        "상": "hard", "중": "medium", "하": "easy"
    }

    def normalize(self, metadata: dict) -> dict:
        """메타데이터 정규화"""
```

---

## 7. 검증 체크리스트

| 코드 | 검증 항목 | 실패 시 처리 |
|------|----------|-------------|
| V001 | 파일 존재 여부 | 요청 반려 |
| V002 | XML 스키마 유효성 | 요청 반려 |
| V003 | 이미지 포맷 | 요청 반려 |
| V004 | 이미지 크기 | 요청 반려 |
| V005 | 필수 메타데이터 | 기본값 적용 |
| V006 | 과목 코드 | 요청 반려 |
| V007 | 이미지 경로 유효성 | 경고 기록 |

---

## 8. 오류 코드

| 코드 | 의미 | HTTP 상태 |
|------|------|----------|
| E001-001 | QTI/IML 파싱 실패 | 400 |
| E001-002 | 지원하지 않는 포맷 | 400 |
| E001-003 | 이미지 포맷 오류 | 400 |
| E001-004 | 이미지 크기 초과 | 400 |
| E001-005 | 필수 필드 누락 | 400 |
| E001-006 | 인코딩 오류 | 400 |
| E001-007 | 이미지 파일 없음 | 400 |

---

## 9. 저장

```
output/
└── p1_input/
    └── {request_id}.json    # InputPack JSON
```

---

**문서 끝**
