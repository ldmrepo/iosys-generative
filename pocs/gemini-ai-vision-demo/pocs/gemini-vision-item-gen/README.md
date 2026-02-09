# Gemini Vision Item Generator POC

Gemini 3 Flash의 Agentic Vision 기능을 활용한 AI 문항 생성 시스템 POC

> 📌 최종 시스템 명세는 [docs/specs/](../../docs/specs/) 폴더를 참조하세요.

---

## 개요

이미지(그래프, 도형, 수식 등)를 분석하여 자동으로 교육용 문항을 생성하는 시스템

### 핵심 기술

- **Gemini Agentic Vision**: Think-Act-Observe 루프 기반 능동적 시각 탐색
- **자동 문항 생성**: 발문/선지/정답/해설 자동 생성
- **이미지 생성**: Nano Banana Pro (gemini-3-pro-image-preview)
- **자동 검수**: 규칙 기반 + AI 기반 정합성 검증

---

## 설치

```bash
# 1. 의존성 설치
pip install -e .

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY 설정
```

---

## 사용법

### 1. 샘플 이미지 생성 (테스트용)

```bash
python scripts/generate_samples.py
```

### 2. 문항 생성

```bash
# CLI 사용
python -m src.cli generate samples/images/bar_chart_1.png --type graph

# 옵션
#   --type, -t: 문항 유형 (graph, geometry, measurement)
#   --difficulty, -d: 난이도 (easy, medium, hard)
#   --validate/--no-validate: 검수 수행 여부
#   --output, -o: 출력 디렉토리
```

### 3. POC 전체 실행

```bash
python scripts/run_poc.py
```

### 4. 기존 문항 검수

```bash
python -m src.cli validate-item output/items/ITEM-XXXXXXXX.json
```

---

## 프로젝트 구조

```
gemini-vision-item-gen/
├── src/                        # 소스 코드
│   ├── agents/                 # AI 에이전트
│   │   ├── vision_client.py    # Gemini Vision 클라이언트
│   │   ├── item_generator.py   # 문항 생성 에이전트
│   │   └── nano_banana_client.py
│   ├── core/                   # 핵심 로직
│   │   ├── config.py           # 설정 관리
│   │   └── schemas.py          # 데이터 모델
│   ├── integrations/           # 외부 연동
│   ├── validators/             # 검수 모듈
│   ├── utils/                  # 유틸리티
│   ├── cli.py                  # CLI 인터페이스
│   └── pipeline.py             # 통합 파이프라인
├── scripts/                    # 실행 스크립트
├── tests/                      # 단위 테스트
├── samples/                    # 샘플 데이터
│   ├── images/                 # 문항 이미지
│   └── exams/                  # 시험지 PDF
├── output/                     # 출력물
│   ├── items/                  # 생성된 문항 JSON
│   ├── logs/                   # 실행 로그
│   └── nano_banana/            # 생성된 이미지
└── docs/                       # POC 관련 문서
    └── planning/               # 계획 문서
```

---

## 지원 문항 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| `graph` | 그래프 해석형 | 막대/선/원 그래프, 함수 그래프 |
| `geometry` | 도형 인식형 | 삼각형, 사각형, 각도, 좌표 |
| `measurement` | 측정값 판독형 | 자, 저울, 온도계 |

---

## 출력 예시

```json
{
  "item_id": "ITEM-A1B2C3D4",
  "item_type": "graph",
  "difficulty": "medium",
  "stem": "위 그래프에서 3월의 판매량은 얼마인가?",
  "choices": [
    {"label": "①", "text": "45개"},
    {"label": "②", "text": "55개"},
    {"label": "③", "text": "65개"},
    {"label": "④", "text": "75개"},
    {"label": "⑤", "text": "85개"}
  ],
  "correct_answer": "②",
  "explanation": "그래프에서 3월 막대의 높이를 확인하면 55개입니다."
}
```

---

## 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `GOOGLE_API_KEY` | Google AI API 키 | (필수) |
| `GEMINI_MODEL` | 사용할 모델 | `gemini-3-flash-preview` |
| `OUTPUT_DIR` | 출력 디렉토리 | `./output` |
| `LOG_LEVEL` | 로그 레벨 | `INFO` |

---

## 관련 문서

### 시스템 명세 (프로젝트 루트)

| 문서 | 설명 |
|------|------|
| [시스템 명세](../../docs/specs/QTI-ITEM-GEN-SYSTEM-SPEC.md) | 전체 시스템 명세 |
| [파이프라인 명세](../../docs/specs/pipeline/README.md) | P1-P5 파이프라인 |

### POC 문서

| 문서 | 설명 |
|------|------|
| [POC 계획](docs/planning/POC-PLAN-001.md) | POC 실행 계획 |

---

## 라이선스

MIT License
