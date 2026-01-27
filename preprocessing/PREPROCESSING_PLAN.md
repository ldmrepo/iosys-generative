# IML 데이터 전처리 계획서

**작성일**: 2026-01-27
**상태**: 승인 대기

---

## 1. 목표

IML(문항 XML) 원본 데이터를 분석하고, POC 및 임베딩 파이프라인에 적합한 형태로 전처리

---

## 2. 프로젝트 구조

```
preprocessing/
├── scripts/
│   ├── 01_extract_schema.py      # 스키마 추출
│   ├── 02_parse_iml.py           # IML 파싱
│   ├── 03_preprocess.py          # 전처리 (정제, 변환)
│   └── utils/
│       ├── iml_parser.py         # IML 파서 유틸리티
│       └── latex_converter.py    # LaTeX 변환 유틸리티
├── output/
│   ├── items.json                # 전처리된 문항 데이터
│   ├── items.parquet             # 분석용 Parquet
│   └── statistics.json           # 데이터 통계
├── schemas/
│   ├── iml_tags.json             # 추출된 태그 스키마
│   ├── iml_attributes.json       # 추출된 속성 스키마
│   └── output_schema.json        # 출력 데이터 스키마
└── PREPROCESSING_PLAN.md
```

---

## 3. 단계별 계획

### Phase 1: 스키마 추출 (01_extract_schema.py)

**목적**: 모든 IML 파일에서 사용되는 태그와 속성을 수집하여 스키마 정의

**작업 내용**:
1. 전체 11,598개 IML 파일 스캔
2. 모든 XML 태그 수집 (중복 제거)
3. 각 태그별 속성(attribute) 수집
4. 속성별 값 샘플 및 패턴 분석
5. 태그 계층 구조 파악

**산출물**:
- `schemas/iml_tags.json`: 태그 목록 및 계층 구조
- `schemas/iml_attributes.json`: 속성별 값 패턴

---

### Phase 2: IML 파싱 (02_parse_iml.py)

**목적**: IML 파일을 구조화된 Python 객체로 변환

**작업 내용**:
1. EUC-KR → UTF-8 인코딩 변환
2. XML 파싱 (ElementTree 또는 lxml)
3. 문항 메타데이터 추출:
   - id, 난이도(df), 문항유형(qt)
   - 분류체계(cls1~cls9), 키워드(kw)
   - 출제년도(dyear), 출처(qs)
4. 콘텐츠 추출:
   - 문제 본문 (텍스트 + 수식)
   - 보기 (답항 1~5)
   - 정답
   - 해설
5. 이미지 경로 매핑 및 존재 여부 확인

**산출물**:
- 파싱된 문항 객체 리스트

---

### Phase 3: 전처리 (03_preprocess.py)

**목적**: 임베딩 및 검색에 적합한 형태로 데이터 정제

**작업 내용**:

#### 3.1 텍스트 정제
- XML 태그 제거
- 불필요한 공백/개행 정규화
- 특수문자 처리

#### 3.2 수식 처리
- LaTeX 수식 추출 및 보존
- 옵션 A: LaTeX 그대로 유지 (`$...$` 형식)
- 옵션 B: 텍스트 변환 (읽기 가능한 형태)
- 옵션 C: 수식 이미지 렌더링

#### 3.3 이미지 처리
- 이미지 경로 정규화 (Windows → Unix)
- 이미지 존재 여부 검증
- 이미지 메타데이터 추출 (크기, 형식)

#### 3.4 분류 체계 정규화
- cls1~cls9 값 파싱 및 정규화
- 코드-라벨 매핑 테이블 생성

#### 3.5 데이터 검증
- 필수 필드 존재 여부
- 정답 범위 검증 (1~5)
- 중복 문항 ID 검출

**산출물**:
- `output/items.json`: 전처리된 문항 데이터
- `output/statistics.json`: 데이터 통계

---

## 4. 출력 데이터 스키마 (안)

```json
{
  "id": "2D444927B7AD4513AFF63DCEAFC13A37",
  "metadata": {
    "difficulty": "상",
    "question_type": "선택형",
    "curriculum": "2015개정교육과정",
    "school_level": "중학교",
    "grade": "2학년",
    "subject": "수학",
    "semester": "2학기",
    "unit_large": "삼각형과 사각형의 성질",
    "unit_medium": "사각형의 성질",
    "unit_small": "여러 가지 사각형 사이의 관계",
    "keywords": ["여러", "가지", "사각형"],
    "year": 2014,
    "source": "2015개정 복사 문항"
  },
  "content": {
    "question": "오른쪽 그림에서 정사각형 $ABCD$의 한 변의 길이가 $8~cm$이고...",
    "choices": [
      "$4~cm^2$",
      "$5~cm^2$",
      "$6~cm^2$",
      "$8~cm^2$",
      "$9~cm^2$"
    ],
    "answer": 4,
    "explanation": "BD를 그으면 AE∥BC이므로..."
  },
  "images": {
    "question": ["images/2D444927.../P04B18888.png"],
    "explanation": ["images/2D444927.../P04B65348.png"]
  },
  "has_image": true,
  "raw_latex": {
    "question": ["\\overline{FC} = 6~cm", "△EFC"],
    "choices": [...],
    "explanation": [...]
  }
}
```

---

## 5. 기술 스택

| 구성 요소 | 라이브러리 |
|----------|-----------|
| XML 파싱 | `lxml` 또는 `xml.etree.ElementTree` |
| 인코딩 변환 | `codecs` |
| 데이터 처리 | `pandas` |
| JSON 처리 | `json` |
| 병렬 처리 | `multiprocessing` 또는 `concurrent.futures` |
| 진행률 표시 | `tqdm` |

---

## 6. 예상 이슈 및 대응

| 이슈 | 대응 방안 |
|------|----------|
| 인코딩 오류 | `errors='replace'` 또는 `errors='ignore'` 옵션 |
| 잘못된 XML | `recover=True` 옵션 (lxml) |
| 누락된 이미지 | 로그 기록 후 `has_image=False` 처리 |
| 대용량 처리 | 배치 처리 + 진행률 표시 |

---

## 7. 실행 순서

```bash
# 1. 스키마 추출
python scripts/01_extract_schema.py

# 2. IML 파싱
python scripts/02_parse_iml.py

# 3. 전처리
python scripts/03_preprocess.py
```

---

## 8. 승인 요청 사항

1. **프로젝트 구조** 승인
2. **출력 스키마** 검토 및 수정 요청
3. **수식 처리 방식** 선택:
   - [ ] 옵션 A: LaTeX 원본 유지
   - [ ] 옵션 B: 텍스트 변환
   - [ ] 옵션 C: 이미지 렌더링
4. **Phase 1 (스키마 추출)** 진행 승인

---

**대기 중**: 승인 후 Phase 1 진행
