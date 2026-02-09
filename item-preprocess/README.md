# item-preprocess

교육 문항(IML) 데이터 전처리 및 2022 개정 교육과정 성취기준-교과서 분류 매핑을 수행하는 모듈.

---

## 디렉터리 구조

```
item-preprocess/
├── README.md                              ← 이 문서
│
├── 2022/                                  ← 2022 개정 교육과정 성취기준 CSV (14개)
│   ├── (중등)...성취수준(수학).csv         ← 중등 5개 교과 (매핑 대상)
│   ├── (중등)...성취수준(국어).csv
│   ├── (중등)...성취수준(과학).csv
│   ├── (중등)...성취수준(사회).csv
│   ├── (중등)...성취수준(역사).csv
│   ├── (중등)...성취수준(영어).csv 등      ← 기타 교과 (매핑 미대상)
│   └── README.md                          ← CSV 스키마 및 교과별 상세
│
├── scripts/
│   ├── extract_textbook_classification.py  ← IML → 교과서 분류 추출
│   ├── prepare_mapping_data.py            ← 매핑 입력 데이터 생성
│   ├── merge_mapping_results.py           ← 매핑 결과 병합 (JSON/CSV/SQLite)
│   ├── verify_mapping.py                  ← 매핑 품질 검증
│   └── convert_to_qti.py                 ← IML → QTI 2.1 변환
│
├── mapping_input/                          ← 과목별 매핑 입력 (5개)
│   ├── math_input.json
│   ├── korean_input.json
│   ├── science_input.json
│   ├── social_input.json
│   └── history_input.json
│
├── mapping_output/                         ← 과목별 매핑 결과 (5개)
│   ├── math_mapping.json
│   ├── korean_mapping.json
│   ├── science_mapping.json
│   ├── social_mapping.json
│   └── history_mapping.json
│
├── textbook_classification_2022.json       ← 교과서 분류 체계 (84개 고유 분류)
├── textbook_classification_2022.csv
│
├── curriculum_mapping_2022.json            ← 최종 매핑 결과 (JSON)
├── curriculum_mapping_2022.csv             ← 최종 매핑 결과 (CSV)
├── curriculum_mapping_2022.db              ← 최종 매핑 결과 (SQLite)
├── mapping_verification_report.md          ← 매핑 검증 보고서
│
├── ITEM-AI-ARCH-001.md                     ← 시스템 아키텍처 설계문서
├── ITEM-AI-TECH-STACK-001.md               ← 기술 스택 문서
├── ITEM-DATA-EVAL-001.md                   ← 학습 데이터 준비 및 평가 방법
├── ITEM-GEN-TRAIN-001.md                   ← 문항생성모델 학습 설계문서
├── ITEM-PROMPT-SPEC-001.md                 ← 프롬프트 인터페이스 규격
└── QTI-INTENT-PIPELINE-001.md              ← QTI 기반 출제의도 추출 파이프라인
```

---

## 교과서 분류 체계 (CLS)

IML 문항 파일에서 추출한 2022 개정 교육과정 교과서 단원 분류 체계.

| 필드 | 의미 | 예시 |
|------|------|------|
| cls1 | 교육과정 | `A13 2022개정교육과정` |
| cls2 | 학교급 | `02 중학교` |
| cls3 | 학년 | `07 1학년` |
| cls4 | 과목코드 | `03 수학` |
| cls5 | 과목상세 | `01 수학` |
| cls6 | 학기 | `01 1학기` |
| cls7 | 대단원 | `01 1. 수와 연산` |
| cls8 | 중단원 | `01 소인수분해` |
| cls9 | 소단원 | `03 03. 최대공약수` |

과목코드(cls4):

| 코드 | 과목 | 분류 수 | leaf | intermediate |
|------|------|---------|------|-------------|
| `01` | 국어 | 13 | 13 | 0 |
| `03` | 수학 | 34 | 31 | 3 |
| `04` | 사회 | 15 | 12 | 3 |
| `045` | 역사 | 17 | 15 | 2 |
| `05` | 과학 | 4 | 4 | 0 |
| **합계** | | **83** | **75** | **8** |

> 중복 정규화 후 84 → 83개 (국어 "03. 소설" / "03.소설" 통합)

---

## 교육과정 매핑

교과서 분류(cls 체계)와 2022 개정 교육과정 성취기준 간 1:N 매핑.
LLM 기반 매핑을 수행하고 SQLite DB + JSON/CSV로 저장.

### 매핑 결과 요약

| 항목 | 값 |
|------|-----|
| 교과서 분류 수 | 83 |
| 성취기준 수 | 312 |
| 총 매핑 수 | 207 |
| 교과서 커버리지 | **83/83 (100%)** |
| 성취기준 커버리지 | 145/312 (46.5%) |
| 저신뢰(<0.5) 매핑 | 0 |

### 과목별 상세

| 과목 | 분류 수 | 성취기준 | 매핑 수 | 미매핑 | 평균 신뢰도 | 비고 |
|------|---------|---------|---------|--------|-----------|------|
| 수학 | 34 | 60 | 42 | 39 | 0.923 | 2~3학년 단원 부재 |
| 국어 | 13 | 51 | 52 | 20 | 0.853 | 매체 영역 전체 미매핑 |
| 과학 | 4 | 87 | 7 | 80 | 0.921 | 분류 극소, 대부분 미매핑 |
| 사회 | 15 | 74 | 57 | 26 | 0.721 | 지리 영역 전체 미매핑 |
| 역사 | 17 | 40 | 49 | 2 | 0.893 | 거의 완전 매핑 |

> 미매핑 성취기준 167개 중 80개(48%)가 과학 — 교과서 분류가 4개뿐인 구조적 한계.

### SQLite 스키마

```sql
-- 교과서 분류
CREATE TABLE textbook_classifications (
    id TEXT PRIMARY KEY,            -- tb_math_001
    subject TEXT NOT NULL,          -- 수학
    subject_code TEXT NOT NULL,     -- 03
    grade TEXT,                     -- 1학년
    semester TEXT,
    chapter TEXT,                   -- 1. 수와 연산
    section TEXT,                   -- 소인수분해
    subsection TEXT,                -- 03. 최대공약수
    full_path TEXT NOT NULL,        -- 수학 > 1학년 > 1학기 > ...
    is_leaf INTEGER NOT NULL DEFAULT 1,
    cls4 TEXT, cls5 TEXT, cls6 TEXT, cls7 TEXT, cls8 TEXT, cls9 TEXT
);

-- 성취기준
CREATE TABLE achievement_standards (
    code TEXT PRIMARY KEY,          -- [9수01-02]
    subject TEXT NOT NULL,          -- 수학
    description TEXT NOT NULL,
    domain TEXT NOT NULL            -- 수와 연산
);

-- 매핑 (1:N)
CREATE TABLE mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    textbook_id TEXT NOT NULL REFERENCES textbook_classifications(id),
    standard_code TEXT NOT NULL REFERENCES achievement_standards(code),
    confidence REAL NOT NULL DEFAULT 0.0,
    reasoning TEXT,
    UNIQUE(textbook_id, standard_code)
);

CREATE INDEX idx_mappings_textbook ON mappings(textbook_id);
CREATE INDEX idx_mappings_standard ON mappings(standard_code);
```

### 쿼리 예시

```sql
-- 교과서 분류 → 성취기준
SELECT m.standard_code, a.description, m.confidence
FROM mappings m
JOIN achievement_standards a ON m.standard_code = a.code
WHERE m.textbook_id = 'tb_math_001';

-- 성취기준 → 교과서 분류
SELECT m.textbook_id, t.full_path, m.confidence
FROM mappings m
JOIN textbook_classifications t ON m.textbook_id = t.id
WHERE m.standard_code = '[9수01-02]';

-- 과목별 매핑 통계
SELECT t.subject, COUNT(*) as mapping_count, AVG(m.confidence) as avg_conf
FROM mappings m
JOIN textbook_classifications t ON m.textbook_id = t.id
GROUP BY t.subject;
```

---

## QTI 2.1 변환

IML 문항을 QTI(Question and Test Interoperability) 2.1 표준 XML로 변환.
후속 파이프라인(Curriculum Retrieval, Intent Generation)의 입력 데이터로 사용.

### 변환 결과

| 항목 | 값 |
|------|-----|
| 원본 IML 스캔 | 184,761건 |
| A13(2022교육과정) 매치 | 49,328건 |
| 변환 성공 | **49,328건 (100%)** |
| 변환 오류 | 0건 |
| 이미지 복사 | 14,342건 (누락 0) |
| 출력 용량 | 1.9 GB |

### 과목별 분포 (상위)

| 과목 | 문항 수 | 비율 |
|------|---------|------|
| 수학 | 14,812 | 30.0% |
| 영어 | 7,404 | 15.0% |
| 국어 | 7,373 | 14.9% |
| 사회 | 6,701 | 13.6% |
| 역사 | 5,451 | 11.1% |
| 과학 | 4,949 | 10.0% |
| 기타 | 2,638 | 5.4% |

### 문항유형 → QTI Interaction 매핑

| IML 유형 | QTI Interaction | 문항 수 |
|----------|-----------------|---------|
| 선택형(11) | `choiceInteraction` | 34,772 |
| 완결형(34) / 단답형(31) | `textEntryInteraction` | 13,804 |
| 서술형(41) / 논술형(51) | `extendedTextInteraction` | 752 |

### 출력 구조

```
data/qti/2022/
├── {item_id}/
│   ├── item.xml              # QTI 2.1 assessmentItem
│   └── images/               # 이미지 (해당 문항만)
│       └── *.png / *.jpg
└── conversion_report.json    # 변환 통계
```

> 상세 통계는 `data/qti/DATA-SUMMARY.md` 참조

---

## 스크립트 실행 순서

### 1. 교과서 분류 추출 (선행 완료)

```bash
python scripts/extract_textbook_classification.py
```

IML 원본에서 cls1~cls12 추출 → `textbook_classification_2022.json`, `.csv` 생성.

### 2. 매핑 입력 데이터 준비

```bash
python scripts/prepare_mapping_data.py
```

교과서 분류 JSON + 성취기준 CSV를 로드하여 과목별 입력 파일 생성.

- 번호 prefix 정제 (e.g. "01 1. 수와 연산" → "1. 수와 연산")
- 중복 정규화 ("03. 소설" / "03.소설" 통합)
- leaf/intermediate 자동 판별
- 출력: `mapping_input/{subject}_input.json` (5개)

### 3. LLM 매핑 (병렬)

5개 과목에 대해 LLM agent가 각각 입력 파일을 읽고 매핑을 수행.
domain-chapter 사전 매칭으로 검색 범위를 축소한 후, 의미적 매칭으로 confidence 점수 산출.

- 출력: `mapping_output/{subject}_mapping.json` (5개)

### 4. 결과 병합

```bash
python scripts/merge_mapping_results.py
```

5개 과목 매핑 결과를 병합하여 3가지 형식으로 저장.

- 출력: `curriculum_mapping_2022.json`, `.csv`, `.db`

### 5. 검증

```bash
python scripts/verify_mapping.py
```

4가지 검증 수행:

1. **교과서 커버리지**: 모든 분류에 1개 이상 매핑 존재 여부
2. **성취기준 역커버리지**: 미매핑 성취기준 목록 (과학 예외 허용)
3. **도메인 일관성**: 같은 도메인 성취기준의 단원 매핑 일관성
4. **신뢰도 분포**: 과목별 평균/최소/최대, 저신뢰 목록

- 출력: `mapping_verification_report.md`

### 6. QTI 2.1 변환

```bash
# 전체 변환 (2022 교육과정)
python scripts/convert_to_qti.py \
  --input-dir ../../data/raw \
  --output-dir ../../data/qti/2022

# 과목 필터
python scripts/convert_to_qti.py \
  --input-dir ../../data/raw \
  --output-dir ../../data/qti/2022 \
  --subject 수학

# 단일 파일 변환
python scripts/convert_to_qti.py \
  --input-file ../../data/raw/2024/06/17/ITEM_ID.iml \
  --output-dir /tmp/qti_test

# 테스트 (최대 N건)
python scripts/convert_to_qti.py \
  --input-dir ../../data/raw \
  --output-dir ../../data/qti/2022 \
  --limit 100
```

IML 문항을 QTI 2.1 assessmentItem XML로 변환. 이미지 자동 복사, 교육과정 메타데이터(`iosys:metadata`) 확장 포함.

- 의존: `preprocessing/scripts/utils/iml_parser.py`, `latex_cleaner.py`
- 출력: `data/qti/2022/{item_id}/item.xml` + `images/` + `conversion_report.json`

---

## 설계 문서 목록

| 문서 ID | 제목 | 내용 |
|---------|------|------|
| ITEM-AI-ARCH-001 | 통합 시스템 아키텍처 | 멀티에이전트 협업 구조 설계 |
| ITEM-AI-TECH-STACK-001 | 기술 스택 | 온프레미스 멀티모델 기술 전략 |
| ITEM-DATA-EVAL-001 | 학습 데이터 준비 및 평가 | 데이터셋 구성/정제 및 정량 평가 |
| ITEM-GEN-TRAIN-001 | 문항생성모델 학습 설계 | 성취기준 기반 문항 생성 모델 |
| ITEM-PROMPT-SPEC-001 | 프롬프트 인터페이스 규격 | 학습/추론/평가 입력 형식 통일 |
| QTI-INTENT-PIPELINE-001 | QTI 출제의도 추출 파이프라인 | QTI → 성취기준/출제의도 자동 추출 |

---

## 데이터 출처

| 항목 | 값 |
|------|-----|
| 교육과정 | 2022 개정 교육과정 |
| 성취기준 원본 | NCIC(국가교육과정정보센터) HWP → CSV 변환 |
| 교과서 분류 원본 | IML 문항 파일 41,372건 중 2022 교육과정 6,378건 |
| QTI 변환 대상 | IML 문항 파일 184,761건 중 2022 교육과정 49,328건 |
| 매핑 방법 | LLM 기반 의미 매칭 (domain 사전매칭 + 내용 매칭) |
