# 작업 히스토리

## 프로젝트 개요

**목적**: Gemini Agentic Vision API를 활용한 PDF 시험지 문항 자동 추출 POC

**저장소**: https://github.com/ldmrepo/gemini-ai-vision-demo

---

## 작업 완료 내역

### 1. PDF 문항 추출 POC 구현 (2026-02-01)

#### 1.1 프로젝트 구조

```
pocs/pdf-item-extractor/
├── scripts/
│   └── run_extraction.py      # 실행 스크립트
├── src/
│   ├── agents/
│   │   └── agentic_vision_client.py  # Gemini Vision API 클라이언트
│   ├── core/
│   │   ├── config.py          # 설정 (API 키, DPI 등)
│   │   └── schemas.py         # 데이터 스키마
│   ├── extractors/
│   │   └── pdf_extractor.py   # PDF 처리 및 시각화
│   └── pipeline.py            # 추출 파이프라인
├── .env                       # 환경변수 (gitignore)
├── .gitignore
└── requirements.txt
```

#### 1.2 핵심 기능

1. **PDF → 이미지 변환**: PyMuPDF(fitz) 사용, DPI 설정 가능
2. **문항/지문 감지**: Gemini 3 Flash Vision API
3. **bbox 추출**: 정규화 좌표(0-1000) → 픽셀 변환
4. **시각화**: 문항(색상 박스), 지문(주황 반투명)

#### 1.3 Gemini API 좌표 형식 (중요)

```python
# Gemini 반환 형식
box_2d = [ymin, xmin, ymax, xmax]  # 0-1000 정규화

# 픽셀 변환
y1 = int(box_2d[0] / 1000 * height)
x1 = int(box_2d[1] / 1000 * width)
y2 = int(box_2d[2] / 1000 * height)
x2 = int(box_2d[3] / 1000 * width)
```

#### 1.4 해결한 이슈들

| 문제 | 원인 | 해결 |
|------|------|------|
| bbox 위치 부정확 | 좌표 형식 오류 (`[x1,y1,x2,y2]` 사용) | `[ymin,xmin,ymax,xmax]` 형식으로 수정 |
| 일부 페이지 0개 반환 | API 응답이 배열(`[...]`)로 올 때 파싱 실패 | `_extract_json()`에서 배열 처리 추가 |
| 지문 미감지 | 문항만 감지하는 프롬프트 | 지문+문항 통합 감지 프롬프트로 변경 |

#### 1.5 테스트 결과

| PDF | 페이지 | 문항 | 지문 | 결과 |
|-----|--------|------|------|------|
| 수학-g10 | 12 | 28 | 0 | ✓ |
| 한국사-g12 | 4 | 20 | 0 | ✓ |
| 영어-g12 | 8 | 45 | 다수 | ✓ |
| 물리학-g11 | 4 | 20 | - | ✓ |

---

### 2. 프롬프트 설계

#### 2.1 현재 프롬프트 (영문, 일반화)

```python
prompt = """Analyze this exam page and detect all passages and items.

## Definitions

**Passage**: Shared reading material for multiple items
- Header pattern: "[37~38]", "[41~42]", "다음 글을 읽고" etc.
- Contains long text shared by 2+ items
- May span across columns (return multiple box_2d)

**Item**: Individual question with choices
- Number pattern: "37.", "38." etc.
- Contains question text and choices (①②③④⑤)
- If belongs to a passage, include passage_ref

## Output Format

box_2d: [ymin, xmin, ymax, xmax] normalized 0-1000

{
  "passages": [{
    "passage_id": "37-38",
    "item_range": "37~38",
    "box_2d": [ymin, xmin, ymax, xmax],
    "box_2d_list": [[...], [...]]  // 단 넘김 시
  }],
  "items": [{
    "item_number": "37",
    "box_2d": [ymin, xmin, ymax, xmax],
    "passage_ref": "37-38"  // 지문 참조
  }]
}
```

#### 2.2 API 설정

```python
config = types.GenerateContentConfig(
    response_mime_type="application/json",
    temperature=0.1,
)
```

---

### 3. 데이터 스키마

#### 3.1 ExtractedItem

```python
class ExtractedItem(BaseModel):
    item_number: str           # 문항 번호
    page_number: int           # 페이지 번호
    bbox: BoundingBox          # 바운딩 박스
    item_type: ItemType        # standalone / passage_group
    passage_ref: Optional[str] # 지문 참조 ID
    confidence: float          # 신뢰도
    image_path: Optional[str]  # 크롭 이미지 경로
```

#### 3.2 PassageInfo

```python
class PassageInfo(BaseModel):
    passage_id: str            # 지문 ID (예: "37-38")
    page_number: int           # 페이지 번호
    bbox: BoundingBox          # 메인 bbox
    bbox_list: list[BoundingBox]  # 다중 bbox (단 넘김 시)
    item_range: str            # 문항 범위 (예: "37~38")
    image_path: Optional[str]  # 크롭 이미지 경로
```

---

## 미완료 작업 (TODO)

### Issue #1: 지시/지문 구분

**현재**: 지시와 지문 본문을 하나로 처리
```
[37~38] 다음 글을 읽고...  ← 지시(Instruction)
Philosophy allows us...    ← 지문(Passage) 본문
```

**목표**: 지시와 지문 본문 별도 bbox 추출

**구현 방안**:
- `PassageInfo`에 `instruction_bbox` 필드 추가
- 프롬프트에 `instruction_box_2d`, `content_box_2d` 분리 요청

---

## 실행 방법

### 환경 설정

```bash
cd pocs/pdf-item-extractor

# 가상환경 생성
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY 설정
```

### 실행 명령어

```bash
# 기본 실행 (수학 PDF, 전체 페이지)
python scripts/run_extraction.py --dpi 150

# 특정 PDF 실행
python scripts/run_extraction.py --pdf "../datas/ebsi-2025-exam-eng-영어-even-g12-202511.pdf" --dpi 100

# 특정 페이지만 실행
python scripts/run_extraction.py --pdf "../datas/파일명.pdf" --pages 7-8 --dpi 100
```

### 출력 결과

```
output/
├── segmented/
│   └── {pdf_name}/
│       ├── page_1_segmented.png  # 시각화 이미지
│       ├── page_2_segmented.png
│       └── ...
└── {pdf_name}_extraction.json    # 추출 결과 JSON
```

---

## 참고 자료

### Gemini Agentic Vision 문서

- [Bounding Box Detection - Vertex AI](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/bounding-box-detection)
- [Image Understanding - Gemini API](https://ai.google.dev/gemini-api/docs/image-understanding)
- [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3)

### 좌표 형식 요약

| 항목 | 값 |
|------|-----|
| 형식 | `[ymin, xmin, ymax, xmax]` |
| 범위 | 0-1000 정규화 |
| 원점 | 좌상단 |

---

## 커밋 히스토리

```
d4aeac9 feat: Gemini Agentic Vision 기반 PDF 문항 추출 POC 구현
```

---

## 다음 작업자 가이드

1. **이슈 #1 작업 시**: `schemas.py`와 `agentic_vision_client.py` 수정
2. **새 PDF 테스트 시**: `pocs/datas/`에 PDF 추가 후 실행
3. **프롬프트 수정 시**: `agentic_vision_client.py`의 `extract_items_from_page()` 메서드 확인
4. **시각화 수정 시**: `pdf_extractor.py`의 `save_page_with_boxes()` 메서드 확인

---

*최종 업데이트: 2026-02-01*
