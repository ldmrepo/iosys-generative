# IML Preprocessor

IML 문항 데이터 전처리 및 샘플링 도구

## 개요

이 도구는 IOSYS ItemBank의 IML(Item Markup Language) 파일을 파싱하고,
과목/학년별로 층화 샘플링하여 AI 학습 및 평가용 데이터셋을 생성합니다.

## 주요 기능

- **IML 파싱**: EUC-KR 인코딩된 IML XML 파일 파싱 및 UTF-8 변환
- **층화 샘플링**: 과목(6개) × 학년(9개) 조합별 30개씩 샘플링
- **이미지 처리**: DrawObjPic 이미지 자동 복사 및 검증
- **통계 분석**: 원본 데이터의 분포 분석

## 설치

```bash
cd pocs/gemini-ai-vision-demo/pocs/iml-preprocessor
pip install -e .
```

개발 의존성 포함 설치:
```bash
pip install -e ".[dev]"
```

## 사용법

### 샘플링 실행

```bash
# 기본 설정으로 샘플링
iml-preprocess sample

# 옵션 지정
iml-preprocess sample \
    --raw-dir ../../../../data/raw \
    --output-dir ../../../../data/sample \
    --samples 30

# 이미지 없는 문항도 포함
iml-preprocess sample --no-images
```

### 단일 파일 파싱

```bash
# 콘솔에 출력
iml-preprocess parse /path/to/file.iml

# JSON 파일로 저장
iml-preprocess parse /path/to/file.iml -o output.json
```

### 데이터 통계 조회

```bash
iml-preprocess stats --raw-dir ../../../../data/raw
```

### 인코딩 변환

```bash
iml-preprocess convert input.iml output.iml
```

## 출력 구조

샘플링 결과는 다음 구조로 저장됩니다:

```
data/sample/
├── 수학/
│   ├── 초1/
│   │   ├── {item_id}/
│   │   │   ├── item.json       # 파싱된 메타데이터
│   │   │   ├── item.iml        # UTF-8 변환된 IML
│   │   │   └── images/
│   │   │       └── *.png
│   │   └── ...
│   ├── 초2/
│   │   └── ...
│   └── 중3/
│       └── ...
├── 과학/
│   └── ...
└── sampling_report.json        # 샘플링 결과 보고서
```

## 샘플링 대상

### 과목 (cls4)
| 코드 | 과목 |
|------|------|
| 01 | 국어 |
| 02 | 영어 |
| 03 | 수학 |
| 04 | 사회 |
| 05 | 과학 |
| 06 | 역사 |

### 학년 (cls3)
- 초등학교: 초1 ~ 초6
- 중학교: 중1 ~ 중3

### 목표 샘플 수
- 그룹당: 30개
- 총 목표: 6과목 × 9학년 × 30개 = **최대 1,620개**
- 실제 샘플 수는 가용 데이터에 따라 조정됨

## item.json 스키마

```json
{
  "id": "문항 ID",
  "raw_path": "원본 IML 경로",
  "subject": "수학",
  "grade": "중2",
  "school_level": "중학교",
  "question_type": "선택형",
  "difficulty": "중",
  "stem": "문제 본문",
  "choices": ["선택지1", "선택지2", ...],
  "answer": "정답",
  "explanation": "해설",
  "images": ["이미지 경로 목록"],
  "has_images": true,
  "math_expressions": ["수식 목록"],
  "keywords": ["키워드 목록"]
}
```

## 환경 설정

`.env.example`을 `.env`로 복사하여 설정을 커스터마이징할 수 있습니다:

```bash
cp .env.example .env
```

주요 설정:
- `RAW_DATA_DIR`: 원본 IML 데이터 디렉토리
- `SAMPLE_OUTPUT_DIR`: 샘플 출력 디렉토리
- `SAMPLES_PER_GROUP`: 그룹당 샘플 수 (기본: 30)
- `REQUIRE_IMAGES`: 이미지 필수 여부 (기본: true)

## 테스트

```bash
pytest tests/
```

## 라이선스

MIT License
