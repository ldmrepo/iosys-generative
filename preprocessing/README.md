# Preprocessing

IML(XML) 원본 데이터를 전처리하여 구조화된 JSON 형식으로 변환하는 파이프라인입니다.

> **Last Updated**: 2026-01-28
> **Total Items**: 176,443건 (수학, 과학, 영어, 역사, 사회, 국어)

## 폴더 구조

```
preprocessing/
├── scripts/
│   ├── 01_extract_schema.py   # IML 스키마 추출
│   ├── 02_parse_iml.py        # IML 파싱
│   ├── 03_preprocess.py       # 데이터 정제
│   ├── 04_validate.py         # 유효성 검증
│   └── utils/
│       ├── iml_parser.py      # IML 파서 유틸리티
│       └── latex_cleaner.py   # LaTeX 정규화
├── schemas/
│   ├── iml_tags.json          # 태그 계층 구조
│   ├── iml_attributes.json    # 속성 정의
│   └── iml_tag_dictionary.json # 태그 사전
├── output/                    # 임시 출력 (gitignore)
└── README.md
```

## 데이터 흐름

```
data/raw/*.iml (184,761개)
       │
       ▼
┌──────────────────┐
│ 01_extract_schema│ → schemas/*.json
└──────────────────┘
       │
       ▼
┌──────────────────┐
│   02_parse_iml   │ → output/items_parsed.json (176,443개)
└──────────────────┘
       │
       ▼
┌──────────────────┐
│  03_preprocess   │ → output/items.json
└──────────────────┘
       │
       ▼
┌──────────────────┐
│   04_validate    │ → output/validation_report.json
└──────────────────┘
       │
       ▼
data/processed/items_part*.json (176,443개, 18파트)
```

## 실행 방법

```bash
cd preprocessing

# 1. 스키마 추출 (선택)
python scripts/01_extract_schema.py

# 2. IML 파싱
python scripts/02_parse_iml.py

# 3. 전처리
python scripts/03_preprocess.py

# 4. 유효성 검증
python scripts/04_validate.py
```

## 출력 데이터 형식

### 문항 구조 (items_part*.json)

```json
{
  "id": "A6F2B6C4AA7E493196146D925FFDB98E",
  "metadata": {
    "difficulty": "중",
    "question_type": "선택형",
    "grade": "2학년",
    "subject": "수학",
    "semester": "1학기",
    "unit_large": "수와 식",
    "unit_medium": "유리수와 순환소수",
    "unit_small": "순환소수",
    "keywords": ["순환소수", "분수"],
    "year": 2020
  },
  "content": {
    "question": "다음 중 순환소수를 분수로 나타낸 것으로 옳은 것은?",
    "question_latex": ["0.\\overline{3}", "\\cfrac{1}{3}"],
    "choices": ["$0.\\overline{3} = \\cfrac{1}{3}$", "...", "...", "...", "..."],
    "answer": 1,
    "answers": [1],
    "answer_text": "1",
    "explanation": "순환소수 $0.\\overline{3}$은..."
  },
  "images": {
    "question": ["ID/image1.png"],
    "explanation": [],
    "verified": ["ID/image1.png"],
    "missing": []
  },
  "has_image": true
}
```

### 복수정답 문항

```json
{
  "content": {
    "question": "다음 중 옳은 것을 모두 고르면? (정답 2개)",
    "answer": 1,
    "answers": [1, 3],
    "answer_text": "1,3"
  }
}
```

## 통계

| 항목 | 값 |
|------|-----|
| IML 파일 수 | 184,761 |
| 파싱 성공 | 176,443 (95.5%) |
| 유효 문항 | 131,460 (74.5%) |
| 이미지 포함 | 45,368 |
| 텍스트 전용 | 131,075 |

### 과목별 분포
| 과목 | 수량 | 비율 |
|------|------|------|
| 수학 | 80,548 | 45.7% |
| 과학 | 35,125 | 19.9% |
| 영어 | 17,098 | 9.7% |
| 역사 | 14,680 | 8.3% |
| 사회 | 14,614 | 8.3% |
| 국어 | 11,625 | 6.6% |
| 기타 | 2,753 | 1.5% |

### 문항 유형
- 선택형: 113,034
- 완결형: 30,746
- 단답형: 26,450
- 서술형: 5,224
- 기타: 989

### 난이도 분포
- 상: 24,955
- 상중: 3,433
- 중: 103,744
- 중하: 4,478
- 하: 39,833

### 학년 분포
- 1학년: 47,486
- 2학년: 46,346
- 3학년: 34,509
- 4~6학년: 19,095
- 공통/기타: 29,007

### 검증 오류 (참고)
| 오류 유형 | 수량 | 설명 |
|----------|------|------|
| invalid_semester | 33,128 | 학기 형식 차이 (사용 가능) |
| empty_question | 17,470 | 질문 텍스트 없음 |
| insufficient_choices | 1,081 | 선택지 부족 |
| 중복 질문 | 10,631 | 동일 질문 텍스트 |

## LaTeX 정규화

원본 IML의 LaTeX는 문자 간 공백으로 분리되어 있습니다.

| 원본 | 정규화 |
|------|--------|
| `{ 1 0 8 }` | `108` |
| `{ 0 . 5 }` | `0.5` |
| `{ A B C D }` | `ABCD` |
| `{ \overline { F C } }` | `\overline{FC}` |
| `{ \cfrac { 1 } { 2 } }` | `\cfrac{1}{2}` |
| `{ \angle A }` | `∠A` |

## IML 태그 구조

```
문항종류 (ROOT)
└── 단위문항
    └── 문항
        ├── 문제
        │   ├── 물음 (질문 텍스트)
        │   │   ├── 단락 → 문자열, 수식, 그림
        │   │   └── 보기
        │   └── 답항 (선택지 1~5)
        ├── 정답
        ├── 해설
        └── QUIZLINK
```

자세한 태그 정의는 `schemas/iml_tag_dictionary.json` 참조.

## 주요 클래스

### IMLParser (utils/iml_parser.py)

```python
from utils.iml_parser import IMLParser, parse_iml_file

# 단일 파일 파싱
item = parse_iml_file(Path("data/raw/20200721/ID.iml"))
print(item.content.question_text)
print(item.content.choices)
print(item.content.answer)
```

### LaTeX Cleaner (utils/latex_cleaner.py)

```python
from utils.latex_cleaner import clean_latex, clean_latex_in_text

# LaTeX 정규화
clean_latex("{ 1 0 8 }")  # → "108"
clean_latex("{ \\cfrac { 1 } { 2 } }")  # → "\\cfrac{1}{2}"

# 텍스트 내 인라인 LaTeX 정규화
clean_latex_in_text("값은 ${ 1 0 8 }$이다")  # → "값은 $108$이다"
```

## 전처리 데이터 로드

```python
import json
from pathlib import Path

def load_processed_items():
    """전처리된 문항 데이터 로드"""
    items = []
    processed_dir = Path("data/processed")

    for part_file in sorted(processed_dir.glob("items_part*.json")):
        with open(part_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            items.extend(data['items'])

    return items

# 사용 예
items = load_processed_items()
print(f"Total items: {len(items)}")

# 선택형 문항만 필터링
selective = [i for i in items if i['metadata']['question_type'] == '선택형']

# 이미지 포함 문항
with_image = [i for i in items if i['has_image']]
```
