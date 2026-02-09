# POC 프로젝트 인덱스

AI 기반 문항 생성 시스템 관련 POC (Proof of Concept) 프로젝트 모음

> 📌 최종 시스템 명세는 [docs/specs/](../docs/specs/) 폴더를 참조하세요.

---

## 프로젝트 목록

| 프로젝트 | 설명 | 상태 |
|---------|------|------|
| [gemini-vision-item-gen](gemini-vision-item-gen/) | Gemini Vision 기반 문항 분석 및 생성 POC | 🟢 Active |

---

## gemini-vision-item-gen

### 개요

Gemini 3 Flash의 멀티모달 능력을 활용하여 기존 문항을 분석하고 유사 문항을 생성하는 POC 프로젝트

### 주요 기능

- **Vision 분석**: 문항 이미지에서 그래프, 도형, 수식 추출
- **문항 생성**: 분석 결과 기반 유사/변형 문항 생성
- **이미지 생성**: Nano Banana Pro를 활용한 문항 이미지 생성
- **품질 검증**: 정답 유일성, 계산 검증 등

### 기술 스택

- **Language**: Python 3.11+
- **AI Models**:
  - Gemini 3 Flash (분석/생성)
  - Gemini 3 Pro Image Preview (이미지 생성)
- **Data Format**: QTI 2.1/3.0

### 빠른 시작

```bash
cd pocs/gemini-vision-item-gen

# 환경 설정
cp .env.example .env
# .env 파일에 GOOGLE_API_KEY 설정

# 의존성 설치
pip install -e .

# POC 실행
python scripts/run_poc.py --image samples/images/math_01.png
```

### 관련 문서

- [시스템 명세](../docs/specs/QTI-ITEM-GEN-SYSTEM-SPEC.md)
- [파이프라인 명세](../docs/specs/pipeline/README.md)
- [POC 계획](gemini-vision-item-gen/docs/planning/POC-PLAN-001.md)

---

## 향후 POC 계획

| 프로젝트 | 설명 | 예정 |
|---------|------|------|
| multi-model-validator | 멀티 모델 교차 검증 POC | TBD |
| qti-converter | QTI 2.1 ↔ 3.0 변환기 POC | TBD |
| curriculum-matcher | 교육과정 성취기준 매칭 POC | TBD |

---

**마지막 업데이트**: 2026-02-01
