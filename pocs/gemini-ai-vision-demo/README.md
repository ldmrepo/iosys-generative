# AI 문항 생성 시스템

Gemini Vision 기반 QTI 문항 분석 및 생성 시스템

---

## 프로젝트 구조

```
gemini-ai-vision-demo/
├── docs/                       # 프로젝트 문서
│   ├── specs/                  # 시스템 명세 문서
│   │   ├── QTI-ITEM-GEN-SYSTEM-SPEC.md
│   │   └── pipeline/           # 파이프라인 명세 (P1-P5)
│   └── research/               # 연구 문서
└── pocs/                       # POC 프로젝트
    └── gemini-vision-item-gen/ # Gemini Vision POC
```

---

## 문서

### 시스템 명세 (docs/specs/)

| 문서 | 설명 |
|------|------|
| [시스템 명세](docs/specs/QTI-ITEM-GEN-SYSTEM-SPEC.md) | 전체 시스템 아키텍처 및 명세 |
| [파이프라인 명세](docs/specs/pipeline/README.md) | P1-P5 파이프라인 상세 |

### 연구 문서 (docs/research/)

| 문서 | 설명 |
|------|------|
| [Nano Banana Pro 연구](docs/research/NANO-BANANA-PRO-RESEARCH.md) | Gemini 3 Pro Image 모델 분석 |

### POC 프로젝트 (pocs/)

| 프로젝트 | 설명 | 상태 |
|---------|------|------|
| [gemini-vision-item-gen](pocs/gemini-vision-item-gen/) | Gemini Vision 기반 문항 생성 POC | 🟢 Active |

---

## 핵심 기술

- **Gemini 3 Flash**: 멀티모달 Vision 분석 및 문항 생성
- **Nano Banana Pro**: 교육용 이미지 생성 (gemini-3-pro-image-preview)
- **Multi-Model Validation**: GPT-4o, Claude, Qwen 등 교차 검증
- **Code Execution**: Python/SymPy 기반 계산 검증

---

## 파이프라인 개요

```
P1-INPUT → P2-ANALYZE → P3-GENERATE → P4-VALIDATE → P5-OUTPUT

InputPack → EvidencePack → DraftItem → ValidationReport → FinalItem
```

| 단계 | 기능 | 에이전트 |
|------|------|---------|
| P1 | QTI 파싱, 이미지 검증 | - |
| P2 | Vision 분석, 수식 추출 | AG-VIS |
| P3 | 문항 생성, 오답 설계 | AG-GEN |
| P4 | 정답/사실/안전 검증 | AG-VAL, AG-CALC, AG-FACT, AG-SAFE |
| P5 | 이미지 생성, 표준화 | AG-IMG, AG-STD, AG-AUD |

---

## 빠른 시작

```bash
cd pocs/gemini-vision-item-gen

# 환경 설정
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY 설정

# 의존성 설치
pip install -e .

# POC 실행
python scripts/run_poc.py
```

---

## 라이선스

MIT License
